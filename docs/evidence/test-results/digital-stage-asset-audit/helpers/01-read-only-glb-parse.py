from pathlib import Path
import json, hashlib, struct, math
from datetime import datetime, timezone
import numpy as np
root=Path(r'D:\京剧\京剧\3D人物模型')
out=Path(r'D:\京剧\.runtime\stage-asset-audit-20261029')
out.mkdir(parents=True,exist_ok=True)
CT={5120:('i1',1),5121:('u1',1),5122:('<i2',2),5123:('<u2',2),5125:('<u4',4),5126:('<f4',4)}
COMPS={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT2':4,'MAT3':9,'MAT4':16}
MODE={0:'POINTS',1:'LINES',2:'LINE_LOOP',3:'LINE_STRIP',4:'TRIANGLES',5:'TRIANGLE_STRIP',6:'TRIANGLE_FAN'}
reports=[]
for path in sorted(root.glob('*.glb')):
    data=path.read_bytes(); sha=hashlib.sha256(data).hexdigest()
    rec={'filename':path.name,'sizeBytes':len(data),'sha256':sha,'issues':[]}
    magic,version,length=struct.unpack_from('<4sII',data,0)
    rec['header']={'magic':magic.decode('ascii','replace'),'version':version,'declaredLength':length,'matchesActual':length==len(data)}
    chunks=[];offset=12;doc=None;bin_data=None
    while offset<len(data):
        n,kind=struct.unpack_from('<II',data,offset);start=offset+8
        chunk=data[start:start+n];chunks.append({'offset':offset,'type':hex(kind),'length':n,'withinFile':start+n<=len(data),'aligned4':n%4==0})
        if kind==0x4e4f534a:doc=json.loads(chunk.decode('utf-8'))
        if kind==0x004e4942:bin_data=chunk
        offset=start+n
    rec['chunks']=chunks
    if magic!=b'glTF' or version!=2 or length!=len(data) or offset!=len(data) or not doc or bin_data is None:rec['issues'].append('GLB header/chunk invalid')
    rec['asset']=doc.get('asset',{})
    rec['extensionsUsed']=doc.get('extensionsUsed',[]);rec['extensionsRequired']=doc.get('extensionsRequired',[])
    rec['counts']={name:len(doc.get(name,[])) for name in ['scenes','nodes','meshes','materials','textures','images','accessors','bufferViews','buffers','skins','animations','cameras']}
    rec['buffers']=doc.get('buffers',[])
    rec['externalUris']=[{'kind':kind,'index':i,'uri':item['uri']} for kind in ['buffers','images'] for i,item in enumerate(doc.get(kind,[])) if item.get('uri') and not str(item['uri']).startswith('data:')]
    views=doc.get('bufferViews',[]);acs=doc.get('accessors',[])
    for i,v in enumerate(views):
        if v.get('buffer',0)!=0 or v.get('byteOffset',0)+v['byteLength']>len(bin_data):rec['issues'].append(f'bufferView {i} outside embedded BIN')
    def array(ai):
        a=acs[ai]; n=a['count']; c=COMPS[a['type']]; dtype,size=CT[a['componentType']]
        if 'bufferView' not in a: result=np.zeros((n,c),dtype=dtype)
        else:
            v=views[a['bufferView']];base=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',c*size)
            needed=a.get('byteOffset',0)+(n-1)*stride+c*size if n else 0
            if needed>v['byteLength']:rec['issues'].append(f'accessor {ai} outside view')
            result=np.ndarray(shape=(n,c),dtype=dtype,buffer=bin_data,offset=base,strides=(stride,size)).copy()
        if 'sparse' in a:
            s=a['sparse'];ind=s['indices'];iv=views[ind['bufferView']];idtype,isize=CT[ind['componentType']]
            si=np.frombuffer(bin_data,dtype=idtype,count=s['count'],offset=iv.get('byteOffset',0)+ind.get('byteOffset',0))
            val=s['values'];vv=views[val['bufferView']];sv=np.frombuffer(bin_data,dtype=dtype,count=s['count']*c,offset=vv.get('byteOffset',0)+val.get('byteOffset',0)).reshape((-1,c))
            result[si]=sv
        if a.get('normalized') and a['componentType']!=5126:
            bits=size*8
            result=result.astype(float)/(2**bits-1 if a['componentType'] in [5121,5123,5125] else 2**(bits-1)-1)
            if a['componentType'] in [5120,5122]:result=np.maximum(result,-1)
        return result
    meshes=[];total_tri=total_vertices=totalprimitives=0;geometry=hashlib.sha256(); meshpoints={}
    for mi,m in enumerate(doc.get('meshes',[])):
        prim=[];positions=[]
        for pi,p in enumerate(m.get('primitives',[])):
            mode=p.get('mode',4);pos=array(p['attributes']['POSITION']) if 'POSITION' in p.get('attributes',{}) else None
            vertices=len(pos) if pos is not None else 0
            indices=array(p['indices']).flatten() if 'indices' in p else None
            elements=len(indices) if indices is not None else vertices
            triangles=elements//3 if mode==4 else max(elements-2,0) if mode in [5,6] else 0
            total_tri+=triangles;total_vertices+=vertices;totalprimitives+=1
            if indices is not None and len(indices) and int(indices.max())>=vertices:rec['issues'].append(f'mesh {mi} primitive {pi}: index out of POSITION bounds')
            if pos is not None:
                if not np.isfinite(pos).all():rec['issues'].append(f'mesh {mi} primitive {pi}: nonfinite POSITION')
                positions.append(pos[:,:3].astype(float))
            for semantic,ai in sorted(p.get('attributes',{}).items()):
                geometry.update(semantic.encode());geometry.update(array(ai).tobytes())
            if indices is not None:geometry.update(indices.tobytes())
            prim.append({'mode':MODE.get(mode,str(mode)),'vertices':vertices,'indices':len(indices) if indices is not None else None,'triangles':triangles,'material':p.get('material'),'attributes':list(p.get('attributes',{})),'positionBounds':{'min':pos.min(axis=0).tolist(),'max':pos.max(axis=0).tolist()} if pos is not None and len(pos) else None,'morphTargets':len(p.get('targets',[])),'extensions':p.get('extensions',{})})
        meshes.append({'mesh':mi,'name':m.get('name'),'primitives':prim})
        if positions:meshpoints[mi]=np.concatenate(positions)
    rec['geometry']={'verticesPerPrimitiveSummed':total_vertices,'trianglesPerPrimitiveSummed':total_tri,'primitives':totalprimitives,'decodedAttributesAndIndicesSha256':geometry.hexdigest(),'meshes':meshes}
    nodes=doc.get('nodes',[])
    def matrix(n):
        if 'matrix' in n:return np.array(n['matrix'],float).reshape((4,4),order='F')
        t=np.eye(4);t[:3,3]=n.get('translation',[0,0,0]);s=np.eye(4);s[0,0],s[1,1],s[2,2]=n.get('scale',[1,1,1]);x,y,z,w=n.get('rotation',[0,0,0,1]);q=np.eye(4)
        q[:3,:3]=[[1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w],[2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w],[2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y]]
        return t@q@s
    scene_bounds=[];nodeinfo=[]
    for si,scene in enumerate(doc.get('scenes',[])):
        pts=[]
        def walk(ni,parent,trail):
            if ni in trail:rec['issues'].append('node cycle');return
            n=nodes[ni];world=parent@matrix(n)
            if 'mesh' in n and n['mesh'] in meshpoints:
                p=meshpoints[n['mesh']];p=np.column_stack((p,np.ones(len(p))))@world.T;pts.append(p[:,:3]);nodeinfo.append({'scene':si,'node':ni,'name':n.get('name'),'mesh':n['mesh'],'skin':n.get('skin'),'localTransform':{k:n[k] for k in ['matrix','translation','rotation','scale'] if k in n},'worldBounds':{'min':p[:,:3].min(axis=0).tolist(),'max':p[:,:3].max(axis=0).tolist()}})
            for child in n.get('children',[]):walk(child,world,trail+[ni])
        for ni in scene.get('nodes',[]):walk(ni,np.eye(4),[])
        if pts:
            pts=np.concatenate(pts);lo=pts.min(axis=0);hi=pts.max(axis=0);scene_bounds.append({'scene':si,'name':scene.get('name'),'min':lo.tolist(),'max':hi.tolist(),'dimensions':(hi-lo).tolist(),'skinnedCaveat':'bind-pose local geometry only; no skin deformation evaluated' if doc.get('skins') else None})
    rec['sceneBounds']=scene_bounds;rec['meshNodeInstances']=nodeinfo
    imgs=[]
    for ii,img in enumerate(doc.get('images',[])):
        content=None
        if 'bufferView' in img:
            v=views[img['bufferView']];start=v.get('byteOffset',0);content=bin_data[start:start+v['byteLength']]
        imgs.append({'image':ii,'name':img.get('name'),'mimeType':img.get('mimeType'),'embedded':content is not None,'bytes':len(content) if content is not None else None,'sha256':hashlib.sha256(content).hexdigest() if content is not None else None,'uri':img.get('uri')})
    rec['images']=imgs
    rec['materials']=[{'material':i,'name':m.get('name'),'alphaMode':m.get('alphaMode','OPAQUE'),'doubleSided':m.get('doubleSided',False),'pbrMetallicRoughness':m.get('pbrMetallicRoughness',{}),'normalTexture':m.get('normalTexture'),'occlusionTexture':m.get('occlusionTexture'),'emissiveTexture':m.get('emissiveTexture'),'extensions':m.get('extensions',{})} for i,m in enumerate(doc.get('materials',[]))]
    rec['animationSummary']=[{'name':a.get('name'),'channels':len(a.get('channels',[])),'samplers':len(a.get('samplers',[]))} for a in doc.get('animations',[])]
    rec['skinSummary']=[{'name':s.get('name'),'jointCount':len(s.get('joints',[]))} for s in doc.get('skins',[])]
    rec['baseColorTextureExtract']=None
    for m in doc.get('materials',[]):
        ti=m.get('pbrMetallicRoughness',{}).get('baseColorTexture',{}).get('index')
        if ti is None:continue
        texture=doc.get('textures',[])[ti];ii=texture.get('source')
        if ii is None:
            ii=next((e['source'] for e in texture.get('extensions',{}).values() if isinstance(e,dict) and 'source' in e),None)
        if ii is None:continue
        img=doc['images'][ii]
        if 'bufferView' not in img:continue
        v=views[img['bufferView']];start=v.get('byteOffset',0);content=bin_data[start:start+v['byteLength']]
        ext={'image/png':'.png','image/jpeg':'.jpg','image/webp':'.webp','image/ktx2':'.ktx2'}.get(img.get('mimeType'),'.bin')
        dest=out/f'character-{sha[:16]}-basecolor{ext}'
        if not dest.exists():dest.write_bytes(content)
        rec['baseColorTextureExtract']={'imageIndex':ii,'path':str(dest),'sha256':hashlib.sha256(content).hexdigest(),'bytes':len(content),'kind':'RAW_EMBEDDED_TEXTURE_NOT_3D_RENDER'}
        break
    reports.append(rec)
report={'createdAtUtc':datetime.now(timezone.utc).isoformat(),'kind':'READ_ONLY_USER_CHARACTER_GLB_AUDIT','sourceDirectory':str(root),'sourceFilesModified':False,'paidApiCalls':0,'neural4dCalls':0,'reports':reports,'identicalFiles':[],'identicalDecodedGeometry':[]}
for i,a in enumerate(reports):
    for b in reports[i+1:]:
        if a['sha256']==b['sha256']:report['identicalFiles'].append([a['filename'],b['filename']])
        if a['geometry']['decodedAttributesAndIndicesSha256']==b['geometry']['decodedAttributesAndIndicesSha256']:report['identicalDecodedGeometry'].append([a['filename'],b['filename']])
(out/'character-glb-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'report':str(out/'character-glb-audit.json'),'identicalFiles':report['identicalFiles'],'models':[{'file':r['filename'],'bytes':r['sizeBytes'],'sha256':r['sha256'],'triangles':r['geometry']['trianglesPerPrimitiveSummed'],'vertices':r['geometry']['verticesPerPrimitiveSummed'],'counts':r['counts'],'extensionsRequired':r['extensionsRequired'],'sceneBounds':r['sceneBounds'],'externalUris':r['externalUris'],'issues':r['issues'],'baseColorTextureExtract':r['baseColorTextureExtract']} for r in reports]},ensure_ascii=False,indent=2))
