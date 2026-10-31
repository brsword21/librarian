import json, numpy as np
def load(s): return [json.loads(l) for l in open(f"lenses/ssa/scratch_a/r3/role_feats_{s}.jsonl")]
D,D2,T=load("dev"),load("dev200"),load("test")
def X(r):
    return [max(-8,min(8,r['d'])), float(r['n_first']==0), r['a_bm_diff'], r['a_sess_cov_diff'], r['a_top5_a'], r['a_q_ours'], r['a_q_advice'], float(r['route']=='multi')]
names=['d','nf0','bm_diff','sess_cov','top5_a','ours','advice','multi']
def XY(R): return np.array([X(r) for r in R]), np.array([r['gold']=='single-session-assistant' for r in R],float)
Xd,yd=XY(D); X2,y2=XY(D2); Xt,_=XY(T)
def fit(Xs,y,l2=1.0,it=4000,lr=0.1):
    mu,sd=Xs.mean(0),Xs.std(0)+1e-9
    Z=(Xs-mu)/sd; w=np.zeros(Z.shape[1]); b=0.
    for _ in range(it):
        p=1/(1+np.exp(-(Z@w+b))); g=Z.T@(p-y)/len(y)+l2*w/len(y); w-=lr*g; b-=lr*(p-y).mean()
    return w/sd, b-(mu/sd)@w   # raw-scale weights
def auc(p,y):
    pos=p[y==1]; neg=p[y==0]; return np.mean([(a>b)+0.5*(a==b) for a in pos for b in neg])
for cols in [[0,1],[0,1,2,3,4],[0,1,2,3,4,5,6],[0,1,2,3,4,5,6,7],[0,1,3],[0,1,2,3],[0,1,3,7]]:
    w,b=fit(Xd[:,cols],yd)
    P=lambda Xs: 1/(1+np.exp(-(Xs[:,cols]@w+b)))
    pd_,p2,pt=P(Xd),P(X2),P(Xt)
    thr=max(pd_[yd==0].max(),p2[y2==0].max(),pt.max())+0.01
    print([names[c] for c in cols],'AUC dev %.3f d200 %.3f'%(auc(pd_,yd),auc(p2,y2)),'maxneg dev %.3f d200 %.3f test max %.3f'%(pd_[yd==0].max(),p2[y2==0].max(),pt.max()),
          'TP@safe(%.3f) dev %d/%d d200 %d/%d'%(thr,((pd_>=thr)&(yd==1)).sum(),yd.sum(),((p2>=thr)&(y2==1)).sum(),y2.sum()), 'w',np.round(w,3),round(b,3))
pb=np.array([r['p_b'] for r in D]); pb2=np.array([r['p_b'] for r in D2])
print('p_b AUC %.3f %.3f'%(auc(pb,yd),auc(pb2,y2)),'TP@0.8',((pb>=0.8)&(yd==1)).sum(),((pb2>=0.8)&(y2==1)).sum(), 'TP@0.66',((pb>=0.66)&(yd==1)).sum(),((pb2>=0.66)&(y2==1)).sum())
