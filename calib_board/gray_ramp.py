"""Sample gray patches for approximate white balance and exposure diagnostics."""
import argparse
import cv2
import numpy as np
from .common import DEFAULT_SPEC,read_data,save_json

def analyze(image,detection,spec):
    if image is None: raise ValueError('Cannot read image')
    if (detection['board_id'],detection['spec_version'])!=(spec['board_id'],spec['version']): raise ValueError('Board ID or specification version mismatch')
    if [image.shape[1],image.shape[0]]!=detection['image_size_wh']: raise ValueError('Image resolution mismatch')
    K=np.asarray(detection['K']);D=np.asarray(detection['D']);rv=np.asarray(detection['rvec']);tv=np.asarray(detection['tvec_m'])
    patches=[]
    for g in spec['gray_ramp']:
        x,y,w,h=g['rect_mm']
        # Sample the central 60% on a 20x20 grid to avoid printed edges.
        xx,yy=np.meshgrid(x+np.linspace(.2,.8,20)*w,y+np.linspace(.2,.8,20)*h)
        points=np.c_[xx.ravel(),yy.ravel(),np.zeros(xx.size)]/1000
        if np.min((cv2.Rodrigues(rv)[0]@points.T+tv.reshape(3,1))[2])<=0: raise ValueError('Gray patch lies behind the camera')
        uv=cv2.projectPoints(points,rv,tv,K,D)[0].reshape(20,20,2).astype(np.float32)
        if (uv[:,:,0].min()<0 or uv[:,:,1].min()<0 or uv[:,:,0].max()>=image.shape[1]-1 or uv[:,:,1].max()>=image.shape[0]-1):
            patches.append({'id':g['id'],'valid':False,'reason':'out_of_frame'});continue
        rgb=cv2.remap(image,uv[:,:,0],uv[:,:,1],cv2.INTER_LINEAR)[:,:,::-1].reshape(-1,3)
        patches.append({'id':g['id'],'valid':True,'mean_rgb':rgb.mean(axis=0).tolist(),
                        'std_rgb':rgb.std(axis=0).tolist(),'nominal_srgb':g['nominal_srgb'],
                        'clipped_fraction':float(np.mean(np.any(rgb>=250,axis=1))),
                        'dark_fraction':float(np.mean(np.any(rgb<=5,axis=1)))})
    valid=[p for p in patches if p['valid']]
    if len(valid)<3: raise ValueError('At least three visible gray patches are required')
    brightness=np.array([np.mean(p['mean_rgb']) for p in valid]);nominal=np.array([p['nominal_srgb'][0] for p in valid])
    usable=[p for p in valid if 48<=p['nominal_srgb'][0]<=208 and p['clipped_fraction']<.01 and p['dark_fraction']<.01]
    gain=None
    if usable:
        neutral=np.mean([p['mean_rgb'] for p in usable],axis=0)
        gain=(neutral[1]/neutral).tolist()
    slope,intercept=np.polyfit(nominal,brightness,1)
    fit=slope*nominal+intercept
    return {'patches':patches,'wb_gain_rgb_green_reference':gain,'wb_patch_ids':[p['id'] for p in usable],
            'monotonic_increasing':bool(np.all(np.diff(brightness)>0)),
            'exposure':{'highlight_clipping':any(p['clipped_fraction']>.01 for p in valid),
                        'shadow_crushing':any(p['dark_fraction']>.01 for p in valid)},
            'nominal_code_response':{'slope':float(slope),'intercept':float(intercept),
                                     'rmse_code_values':float(np.sqrt(np.mean((brightness-fit)**2)))},
            'limitation':'Nominal printed sRGB values are not measured reflectances. Code-value fits do not prove radiometric linearity. Assumes unobstructed patches and uniform illumination; not full color correction.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('image');p.add_argument('--detection',required=True)
    p.add_argument('--spec',default=str(DEFAULT_SPEC));p.add_argument('--output',default='build/gray.json');a=p.parse_args()
    save_json(a.output,analyze(cv2.imread(a.image),read_data(a.detection),read_data(a.spec)))
if __name__=='__main__':main()
