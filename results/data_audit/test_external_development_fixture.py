"""Integration exercise of scoring exports on a temporary development-only fixture."""
import copy
import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import joblib
import numpy as np

import mango.external as evaluator
from mango.data import load_development
from mango.optics import get_catalog
from mango.state import digest


def run():
    root=evaluator.ROOT
    development=load_development()
    chosen=np.arange(0,len(development),500)[:12]
    fixture=development.subset(chosen)
    bundle=joblib.load(root/'results/checkpoints/model_season1_uniform_seed42.joblib')
    catalog=get_catalog()
    with tempfile.TemporaryDirectory(prefix='mango_external_dev_fixture_') as directory:
        temp=Path(directory)
        frozen=temp/'results/frozen';frozen.mkdir(parents=True)
        (temp/'data').mkdir()
        (temp/'mango').mkdir()
        shutil.copy2(root/'mango/external.py',temp/'mango/external.py')
        (temp/'data/fixture.txt').write_text('Only development data used in this software test.\n')
        (temp/'data/manifest.json').write_text(json.dumps({'artifacts':{'fixture.txt':digest(temp/'data/fixture.txt')}}))
        config=json.loads((root/'config/experiment.json').read_text())
        config['bootstrap_replicates']=20
        selection={key:'uniform' for key in evaluator.ROLE_KEYS.values()}
        selection['scientific_operating_indices']={'uniform|'+method:10 for method in ['proposed','single']+evaluator.CONTROLS}
        selection['scientific_operating_indices']['uniform|fixed_length']=2
        selection['scientific_operating_indices'].update({'ideal|proposed':10,'ideal|single':10})
        selection['engineering_operating_index']=10
        (frozen/'selection.json').write_text(json.dumps(selection))
        (frozen/'experiment.json').write_text(json.dumps(config))
        (frozen/'catalog.json').write_text(json.dumps(catalog))
        for row in catalog:
            dest=temp/row['profile_path'];dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(root/row['profile_path'],dest)
        runtime={k:v for k,v in bundle.items() if k!='oof'}
        joblib.dump(runtime,frozen/'uniform_seed42.joblib')
        joblib.dump(runtime,frozen/'ideal_seed42.joblib')
        joblib.dump(bundle['rich_predictor'],frozen/'walsh.joblib')
        static={'physical_fixture_8':{'model':bundle['bank_predictor'],'family':'physical',
                 'indices':list(range(8)),'pulses':8,'bank_indices':bundle['bank_indices']}}
        joblib.dump(static,frozen/'static.joblib')
        hashes={str(p.relative_to(temp)):digest(p) for p in temp.rglob('*') if p.is_file()}
        (frozen/'manifest.json').write_text(json.dumps({'status':'frozen','hashes':hashes}))
        access=[]
        def features(season):
            data=copy.deepcopy(fixture)
            data.seasons[:]=season
            data.y=None
            return data
        def targets(season,manifest):
            assert (temp/'results/external_prediction_freeze.json').exists()
            data=copy.deepcopy(fixture)
            data.seasons[:]=season
            access.append(season)
            return data
        def no_fit(*args,**kwargs):
            raise AssertionError('Fitting attempted inside isolated evaluator')
        with patch.object(evaluator,'ROOT',temp),patch.object(evaluator,'load_external_features',features),patch.object(evaluator,'load_external',targets),patch.object(evaluator,'event',lambda message:None),patch.object(evaluator,'ledger',lambda record:None),patch('mango.training.fit_bundle',no_fit):
            result=evaluator.score_external()
            assert result['status']=='complete'
            assert access==[4,5]
            first={p:digest(temp/p) for p in result['outputs']}
            resumed=evaluator.score_external()
            assert resumed==result and access==[4,5]
            assert first=={p:digest(temp/p) for p in result['outputs']}
            # Emulate a crash after an incomplete output and before completion commit.
            (temp/'results/external_completion.json').unlink()
            (temp/'results/external_predictions.csv').write_text('interrupted partial export\n')
            recovered=evaluator.score_external()
            assert recovered['status']=='complete' and access==[4,5,4,5]
            assert first=={p:digest(temp/p) for p in recovered['outputs']}
            outcome={'status':'passed','fixture':'12 actual development spectra relabeled only inside temporary software test; no external assays opened',
                     'prediction_rows':result['prediction_rows'],'metric_rows':result['metric_rows'],'curve_rows':result['curve_rows'],
                     'checks':['every output generated','prediction freeze before target hook','no fit calls','resume no target reload','resume unchanged output hashes','incomplete export recovery reproduces all output hashes without duplicate rows']}
    (root/'results/data_audit/external_fixture_verification.json').write_text(json.dumps(outcome,indent=2)+'\n')
    print(json.dumps(outcome,indent=2))


if __name__=='__main__':run()
