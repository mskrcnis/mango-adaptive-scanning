"""Versioned design-only selection, then evaluation behind a design hash lock."""
import json
import os
import sys
import time
from pathlib import Path

import joblib
import numpy as np
from threadpoolctl import threadpool_limits

from mango.data import load_development
from mango.optics import channel_matrix, get_catalog
from mango.state import atomic_json, canonical_hash, digest
from mango.training import reachable_masks
from revisions.methodology_v2.stopping import fit_stopping, predict_probabilities
from .design import crossfit_design, select_design, FAMILIES

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "results"
V2 = ROOT / "revisions/methodology_v2"
BANKS = {"swap_mid": [0, 2, 3, 4, 5, 7, 8, 9], "uniform": [0, 1, 3, 4, 5, 6, 8, 9]}
CASES = [(s, bank) for s in (1, 2, 3) for bank in BANKS]
READ_PATHS = set()
GUARD = None


def event(message):
    HERE.mkdir(parents=True, exist_ok=True)
    with (HERE / "RUN_STATUS.md").open("a") as stream:
        stream.write("\n- %s: %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S %z"), message))
    print(message, flush=True)


def source_path(held, bank):
    return V2 / "results/checkpoints" / ("case_s%d_%s_seed42.joblib" % (held, bank))


def protected_files():
    result = []
    for name in ("data", "results", "mango", "config", "docs", "figures", "manuscript", "tests",
                 "revisions/methodology_v2"):
        result.extend(p for p in (ROOT/name).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    result.extend(p for p in ROOT.iterdir() if p.is_file() and p.name != "RUN_STATUS.md")
    return sorted(result)


def snapshot():
    path = HERE / "prior_versions_preservation.json"
    if not path.exists():
        atomic_json(path, {"sha256": {str(p.relative_to(ROOT)): digest(p) for p in protected_files()},
                           "exclusion": "Only root RUN_STATUS.md and runtime caches; entire revision 2 protected"})
    return json.loads(path.read_text())


def verify_preservation():
    expected = json.loads((HERE/"prior_versions_preservation.json").read_text())["sha256"]
    changed = [name for name,value in expected.items()
               if not (ROOT/name).exists() or digest(ROOT/name) != value]
    return {"files": len(expected), "changed": changed, "passed": not changed}


def dependencies():
    names = ["pipeline.py", "design.py", "protocol.md"]
    result = {str((HERE/name).relative_to(ROOT)): digest(HERE/name) for name in names}
    for name in ("mango/models.py", "mango/data.py", "mango/optics.py", "mango/training.py",
                 "revisions/methodology_v2/pipeline.py", "revisions/methodology_v2/stopping.py",
                 "data/manifest.json", "data/processed/development.csv", "data/processed/metadata.csv",
                 "data/catalog/catalog.json", "results/fold_assignments.json"):
        result[name] = digest(ROOT/name)
    for path in (ROOT/"data/catalog/profiles").glob("*.csv"):
        result[str(path.relative_to(ROOT))] = digest(path)
    for held,bank in CASES:
        path = source_path(held,bank)
        result[str(path.relative_to(ROOT))] = digest(path)
    return result


def register():
    OUT.mkdir(parents=True, exist_ok=True)
    snapshot()
    deps = dependencies()
    value = {"dependency": canonical_hash(deps), "dependencies": deps, "cases": CASES,
             "banks": BANKS, "families": list(FAMILIES), "external_evaluation": False}
    path = OUT/"registration.json"
    if path.exists() and json.loads(path.read_text()) != value:
        old = json.loads(path.read_text())
        if old["dependency"] != value["dependency"]:
            (OUT/"attempts").mkdir(exist_ok=True)
            (OUT/"attempts"/("registration_%d.json"%time.time())).write_bytes(path.read_bytes())
            event("Dependencies amended; old registration retained; stale checkpoints will rerun.")
    atomic_json(path,value)
    return value


def install_guard(stage):
    """Deny scientific writes outside v3 and source-result reads during design."""
    global GUARD
    if GUARD is not None:
        if GUARD != stage:
            raise RuntimeError("Design and evaluation require separate processes")
        return
    allowed = {p.resolve() for s,b in CASES for p in [source_path(s,b)]}
    def hook(name,args):
        if name != "open" or not isinstance(args[0], (str,bytes,os.PathLike)):
            return
        path = Path(os.fsdecode(args[0])).resolve()
        try:
            relative = path.relative_to(ROOT)
        except ValueError:
            return
        mode, flags = args[1], args[2]
        writing = (isinstance(mode,str) and any(c in mode for c in "wax+")) or (
            isinstance(flags,int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)))
        if writing and HERE not in path.parents and path != HERE:
            raise PermissionError("Prior versions are read-only: "+str(relative))
        if writing:
            return
        parts = relative.parts
        if "sealed" in parts or "external" in path.name.lower():
            raise PermissionError("External data excluded: "+str(relative))
        if parts and parts[0] == "results" and relative != Path("results/fold_assignments.json"):
            raise PermissionError("Version-1 results excluded: "+str(relative))
        if V2/"results" in path.parents:
            if stage != "evaluate" or path not in allowed:
                raise PermissionError("Source predictions unavailable to design: "+str(relative))
        if (parts and parts[0] in ("data","results")) or path in allowed:
            READ_PATHS.add(str(relative))
    sys.addaudithook(hook)
    GUARD = stage


def checkpoint(name,key,fn):
    path = OUT/"checkpoints"/(name+".joblib")
    meta = path.with_suffix(".json")
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and meta.exists():
        old=json.loads(meta.read_text())
        if old.get("status")=="complete" and old.get("dependency")==key and old.get("sha256")==digest(path):
            event("Reused "+name)
            return joblib.load(path)
    started=time.perf_counter()
    atomic_json(meta,{"status":"running","dependency":key})
    event("Started "+name)
    try:
        value=fn()
        tmp=path.with_suffix(".joblib.tmp")
        joblib.dump(value,tmp,compress=3)
        os.replace(str(tmp),str(path))
        atomic_json(meta,{"status":"complete","dependency":key,"sha256":digest(path),
                          "seconds":time.perf_counter()-started})
        event("Completed %s in %.1fs"%(name,time.perf_counter()-started))
        return value
    except BaseException as exc:
        atomic_json(meta,{"status":"failed","dependency":key,"error":repr(exc)})
        event("FAILED "+name+": "+repr(exc))
        raise


def partition_indices(data,assignment):
    mapping={str(row):i for i,row in enumerate(data.row_ids)}
    roles={"fit":"fit_row_ids","design":"bank_design_row_ids","cal":"calibration_row_ids",
           "valid":"validation_row_ids"}
    result={role:np.asarray([mapping[str(row)] for row in assignment[key]],dtype=int) for role,key in roles.items()}
    if set(data.seasons)!={1,2,3} or len(mapping)!=len(data.row_ids):
        raise AssertionError("Unique development rows only")
    groups={role:set(data.groups[ids]) for role,ids in result.items()}
    for a in result:
        for b in result:
            if a!=b and groups[a]&groups[b]:
                raise AssertionError("Population overlaps "+a+"/"+b)
    assert sorted(np.concatenate(list(result.values())).tolist()) == list(range(len(data.row_ids)))
    assert np.all(data.seasons[result["valid"]]==assignment["held_season"])
    assert not np.any(data.seasons[result["design"]]==assignment["held_season"])
    return result


def build_design(data,assignment,bank_indices,centers,checkpoint_fold=None):
    """Only registered design values/assays enter optical prediction or selection."""
    roles=partition_indices(data,assignment)
    ids=roles["design"]
    x=channel_matrix(data.X[ids],data.wavelengths)[:,bank_indices].astype(np.float32)
    y=data.y[ids].astype(float)
    groups=data.groups[ids]
    masks=reachable_masks(8,[0,7])
    fitted=crossfit_design(x,y,groups,masks,folds=len(np.unique(groups)),checkpoint_fold=checkpoint_fold)
    selections={f:select_design(fitted["predictions"][f],y,masks,centers) for f in FAMILIES}
    composition=[{"group":str(g),"season":int(data.seasons[ids[groups==g]][0]),
                  "n":int(np.sum(groups==g))} for g in sorted(set(groups))]
    return {"held_season":assignment["held_season"],"bank_indices":bank_indices,"centers_nm":centers,
            "design_row_ids":data.row_ids[ids],"design_groups":groups,"design_y":y,
            "design_seasons":data.seasons[ids],"composition":composition,
            "role_row_ids":{role:data.row_ids[v] for role,v in roles.items()},
            "role_groups":{role:sorted(set(data.groups[v])) for role,v in roles.items()},
            "crossfit":fitted,"selections":selections}


def features_from_full(full_features,masks,indices):
    """Derive a path from per-channel standardized values, then hide unread values."""
    full=np.asarray(full_features)
    if full.ndim!=2 or full.shape[1]!=16 or not np.all(full[:,8:]==1):
        raise ValueError("Expected eight standardized values and eight full-state availability bits")
    return np.stack([np.concatenate([np.where(masks[j],full[:,:8],0.0),
                                      np.broadcast_to(masks[j],(len(full),8)).astype(full.dtype)],axis=1)
                     for j in indices],axis=1)


def lock_designs(registration):
    files={}
    for held,bank in CASES:
        path=OUT/"checkpoints"/("design_s%d_%s.joblib"%(held,bank))
        meta=json.loads(path.with_suffix(".json").read_text())
        assert meta["status"]=="complete"
        assert meta["dependency"]==canonical_hash([registration["dependency"],"design",held,bank])
        assert meta["sha256"]==digest(path)
        files[str(path.relative_to(HERE))]=digest(path)
    value={"registration_dependency":registration["dependency"],"design_sha256":files,
           "completed_all_designs_before_evaluation":True,"external_evaluation":False}
    atomic_json(OUT/"design_lock.json",value)
    return value


def validate_lock(registration):
    lock=json.loads((OUT/"design_lock.json").read_text())
    assert lock["registration_dependency"]==registration["dependency"]
    assert lock["completed_all_designs_before_evaluation"]
    assert lock["external_evaluation"] is False
    expected={"results/checkpoints/design_s%d_%s.joblib"%(held,bank) for held,bank in CASES}
    assert set(lock["design_sha256"])==expected
    for name,value in lock["design_sha256"].items():
        assert digest(HERE/name)==value
    return lock


def run_design(pilot=False):
    reg=register()
    assignments={r["held_season"]:r for r in json.loads((ROOT/"results/fold_assignments.json").read_text())
                 if r["held_season"] is not None}
    install_guard("design")
    with threadpool_limits(limits=2):
        data=load_development()
        catalog=get_catalog()
        for held,bank in CASES[:1] if pilot else CASES:
            indices=BANKS[bank]
            centers=[catalog[i]["center_nm"] for i in indices]
            callback=lambda fold,fn: checkpoint("designfold_s%d_%s_%d"%(held,bank,fold),
                canonical_hash([reg["dependency"],"designfold",held,bank,fold]),fn)
            checkpoint("design_s%d_%s"%(held,bank),
                       canonical_hash([reg["dependency"],"design",held,bank]),
                       lambda:build_design(data,assignments[held],indices,centers,callback))
        atomic_json(OUT/"design_read_audit.json",{"paths":sorted(READ_PATHS),
                    "source_prediction_reads":False,"external_reads":False,"stage":"design"})
        if not pilot:
            lock_designs(reg)
            event("All six designs locked before source prediction access.")


def evaluate_case(source,design):
    masks=np.asarray(design["crossfit"]["masks"])
    assert np.array_equal(masks,source["masks"])
    assert np.array_equal(design["bank_indices"],source["bank_indices"])
    for split,role in (("train","fit"),("cal","cal"),("valid","valid")):
        assert np.array_equal(source["data"][split]["row_ids"],design["role_row_ids"][role])
        assert set(source["data"][split]["groups"])==set(design["role_groups"][role])
    data={split:{k:v for k,v in info.items() if k!="features"}
          for split,info in source["data"].items()}
    full={split:info["features"][:,-1,:] for split,info in source["data"].items()}
    result={"held_season":source["held_season"],"bank":source["bank"],"bank_indices":source["bank_indices"],
            "masks":masks,"data":data,"full_features":full,"families":{},
            "design_groups":design["role_groups"]["design"]}
    for family in FAMILIES:
        item=source["families"][family]
        selected=design["selections"][family]
        subsets=[selected["by_depth"][str(k)] for k in range(2,9)]
        fresult={"selected_subsets":subsets,
                 "fixed_subset_paths":{s:a[:,subsets] for s,a in item["all_predictions"].items()},
                 "orders":{}}
        for variant in ("catalog","designed"):
            ids=selected["catalog_path_indices"] if variant=="catalog" else selected["path_indices"]
            order=selected["catalog_order"] if variant=="catalog" else selected["order"]
            paths={s:a[:,ids] for s,a in item["all_predictions"].items()}
            features={s:features_from_full(full[s],masks,ids) for s in data}
            if variant=="catalog":
                for s in data:
                    assert np.array_equal(features[s],source["data"][s]["features"])
                    assert np.array_equal(paths[s],item["paths"][s])
                stopping=item["stopping"]
            else:
                a,b=data["train"],data["cal"]
                stopping=fit_stopping(features["train"],paths["train"],paths["train"][:,-1],
                    a["rich"],a["y"],features["cal"],paths["cal"],paths["cal"][:,-1],b["rich"],b["y"],
                    train_groups=a["groups"],cal_groups=b["groups"],seed=42)
            probabilities={s:{objective:predict_probabilities(stopping,features[s],objective)
                              for objective in ("two_reference","single_reference")}
                           for s in ("cal","valid")}
            fresult["orders"][variant]={"order":order,"path_indices":ids,"paths":paths,
                                       "stopping":stopping,"probabilities":probabilities}
        result["families"][family]=fresult
    return result


def run_evaluate():
    reg=json.loads((OUT/"registration.json").read_text())
    assert dependencies()==reg["dependencies"],"Fitting dependencies changed; rerun design first"
    lock=validate_lock(reg)
    install_guard("evaluate")
    with threadpool_limits(limits=2):
        for held,bank in CASES:
            design=joblib.load(OUT/"checkpoints"/("design_s%d_%s.joblib"%(held,bank)))
            path=source_path(held,bank)
            assert digest(path)==reg["dependencies"][str(path.relative_to(ROOT))]
            def compute():
                source=joblib.load(path)
                result=evaluate_case(source,design)
                result.update(source_path=str(path.relative_to(ROOT)),source_sha256=digest(path),
                              design_lock_sha256=digest(OUT/"design_lock.json"))
                return result
            checkpoint("evaluation_s%d_%s"%(held,bank),
                       canonical_hash([reg["dependency"],"evaluation",held,bank,canonical_hash(lock)]),compute)
        atomic_json(OUT/"evaluation_read_audit.json",{"paths":sorted(READ_PATHS),"stage":"evaluate",
                    "external_reads":False,"design_lock_sha256":digest(OUT/"design_lock.json")})
    event("All six evaluation cases completed from locked designs.")
