import subprocess,sys,numpy as np
mp4,t0,dur,x0,y0,x1,y1=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),*map(int,sys.argv[4:8])
w,h=640,360
cmd=['ffmpeg','-loglevel','error','-ss',str(t0),'-t',str(dur),'-i',mp4,'-vf',f'scale={w}:{h}','-r','30','-f','rawvideo','-pix_fmt','rgb24','-']
raw=subprocess.run(cmd,capture_output=True).stdout
n=len(raw)//(w*h*3); a=np.frombuffer(raw,np.uint8)[:n*w*h*3].reshape(n,h,w,3)/255.
lin=np.where(a<=0.04045,a/12.92,((a+0.055)/1.055)**2.4)
Y=(0.2126*lin[...,0]+0.7152*lin[...,1]+0.0722*lin[...,2])
c=Y[:,y0//3:y1//3,x0//3:x1//3].mean(axis=(1,2))
for i,v in enumerate(c): print(f'{t0+i/30:.3f} {v:.3f}')
