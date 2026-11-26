"""Recreate traced typical emission curves from cached manufacturer PDF plots.

Axes are manually read from inspected plots. Dark-curve pixels are traced columnwise;
plot text and frame pixels are excluded. These are digitized typical curves, not
manufacturer numerical measurements. See docs/optics_audit.md.
"""
from pathlib import Path
import csv
import hashlib
import json
import subprocess
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
ROWS = [
 ('LED720-03AU','led720-03au',3,720,23,710,730,(614,827,347,609),(620,820)),
 ('LED740-01AU','led740-series',6,740,30,None,None,(235,394,550,783),(690,790)),
 ('LED760-03AU','led760-series',7,760,30,None,None,(193,455,245,632),(710,810)),
 ('LED780-03AU','led780-03au',3,780,27,770,790,(615,824,348,605),(680,880)),
 ('LED800-01AU','led800-01au',3,800,29,790,810,(598,804,228,482),(700,900)),
 ('LED820-01AU','led820-series',7,820,35,805,835,(195,449,260,636),(770,870)),
 ('LED850-03UP','led850-series',7,850,40,835,865,(202,446,263,625),(750,950)),
 ('LED890-03AU','led890-03au',3,890,47,875,895,(601,807,228,479),(790,990)),
 ('LED910D-01','led910d-01',3,910,35,900,920,(601,807,222,475),(810,1010)),
 ('LED940D-05','led940d-05',3,940,40,930,955,(522,785,895,1218),(780,1080)),
]

def digest(path):
 return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
 cat=[]
 for ident,name,page,center,width,cmin,cmax,box,limits in ROWS:
  source=ROOT/'data/catalog/sources'/f'{name}.pdf'
  out=ROOT/'data/catalog/qa'/name
  subprocess.run(['pdftoppm','-f',str(page),'-l',str(page),'-scale-to','1400','-png','-singlefile',str(source),str(out)],check=True)
  im=Image.open(str(out)+'.png').convert('RGB');gray=np.asarray(im.convert('L'))
  x0,x1,y0,y1=box;lo,hi=limits
  xs=np.arange(x0+2,x1-1)
  vals=[]
  for x in xs:
   wave=lo+(x-x0)/(x1-x0)*(hi-lo)
   ys=np.where(gray[y0+2:y1+1,x]<95)[0]+y0+2
   ys=ys[(ys>y0+0.12*(y1-y0)) | (abs(wave-center)<width)]
   if len(ys)>0:
    yy=float(np.median(ys))
    vals.append(max(0.,min(1.,(y1-yy)/(y1-y0))))
   else: vals.append(float('nan'))
  vals=np.array(vals);good=np.isfinite(vals)
  vals=np.interp(xs,xs[good],vals[good]);vals/=vals.max()
  w=lo+(xs-x0)/(x1-x0)*(hi-lo)
  # Explicit zero endpoints make finite plotted-support treatment reproducible.
  w=np.r_[lo,w,hi];vals=np.r_[0.,vals,0.]
  dest=ROOT/'data/catalog/profiles'/f'{ident}.csv'
  with dest.open('w') as f:
   writer=csv.writer(f);writer.writerow(['wavelength_nm','relative_emission']);writer.writerows(zip(w,vals))
  draw=ImageDraw.Draw(im)
  coords=[(x0+(a-lo)/(hi-lo)*(x1-x0),y1-b*(y1-y0)) for a,b in zip(w,vals)]
  draw.line(coords,fill='red',width=2)
  crop=im.crop((x0-35,y0-25,x1+20,y1+45));crop.save(ROOT/'data/catalog/qa'/f'{ident}_trace_overlay.png')
  fine=np.linspace(lo,hi,10001);v=np.interp(fine,w,vals)
  support=np.trapz(v*((fine>=684)&(fine<=990)),fine)/np.trapz(v,fine)
  half=w[vals>=.5];digitwidth=float(half[-1]-half[0]);digitpeak=float(w[np.argmax(vals)])
  cat.append(dict(id=ident,part_number=ident,manufacturer='Roithner Lasertechnik',center_nm=center,center=center,fwhm_nm=width,fwhm=width,profile_type='digitized_datasheet_curve',profile_path=str(dest.relative_to(ROOT)),profile_sha256=digest(dest),support_fraction=float(support),eligible=bool(support>=.95),source=f'https://www.roithner-laser.com/datasheets/led_div/{name}.pdf',source_path=str(source.relative_to(ROOT)),source_sha256=digest(source),source_page=page,curve_origin='typical manufacturer data-sheet plot, raster digitized at 1400 px page height',wavelength_units='nm',detector_profile='flat assumed; no detector specified or measured',reference_profile='flat assumed; no reference optical spectrum supplied',digitized_peak_nm=digitpeak,digitized_fwhm_nm=digitwidth,center_min_nm=cmin,center_max_nm=cmax,digitization=dict(image_size=im.size,plot_pixels=list(box),plot_wavelengths_nm=list(limits),dark_threshold=95,endpoint_treatment='zero at plot endpoints; zero outside plotted range',overlay=f'data/catalog/qa/{ident}_trace_overlay.png'),notes='Approximate typical curve; not an individually measured emitter or calibrated detector system. Nominal widths and digitized widths may differ.'))
  print(ident,round(support,5),round(digitpeak,1),round(digitwidth,1))
 (ROOT/'data/catalog/catalog.json').write_text(json.dumps(cat,indent=2)+'\n')
 (ROOT/'data/catalog/digitization_parameters.json').write_text(json.dumps({'method':'dark pixel trace with visually calibrated axes','rows':ROWS},indent=2)+'\n')
if __name__=='__main__':main()
