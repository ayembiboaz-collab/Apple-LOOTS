import numpy as np
# Independent ACES AP0 Bradford cross-check against published ASWF matrix.
def prim(p,white):
 a=np.array([[x/y,1,(1-x-y)/y] for x,y in p]).T
 x,y=white; w=np.array([x/y,1,(1-x-y)/y]); return a*np.linalg.solve(a,w)
def white(x,y):return np.array([x/y,1,(1-x-y)/y])
D65=(.3127,.329); D60=(.32168,.33767)
a=prim([(.725,.301),(.221,.814),(.068,-.076)],D65)
ap0=prim([(0.7347,0.2653),(0.,1.),(.0001,-.077)],D60)
b=np.array([[.8951,.2664,-.1614],[-.7502,1.7135,.0367],[.0389,-.0685,1.0296]])
cat=np.linalg.inv(b)@np.diag((b@white(*D60))/(b@white(*D65)))@b
m=np.linalg.solve(ap0,cat@a)
ref=np.array([[.694961049318096,.241405268785364,.06363368189654],[.0473627464149325,1.00429592505428,-.0516586714692158],[-.021989789359883,-.0289891049714743,1.05097889433136]])
print('Max absolute error to ASWF AP0 matrix:',np.max(abs(m-ref))); assert np.max(abs(m-ref))<1e-12
