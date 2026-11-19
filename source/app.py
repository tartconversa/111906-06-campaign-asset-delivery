"""素材原件换签、范围响应与独立渠道交付服务。"""
from .common import *
import struct,zlib,wave
def asset(key,generation):
    if key=='cover':
        def chunk(kind,payload): return struct.pack('!I',len(payload))+kind+payload+struct.pack('!I',zlib.crc32(kind+payload)&0xffffffff)
        pixel=b'\x00'+(b'\x30\x70\xb0' if generation==1 else b'\xb0\x70\x30')*32
        return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',32,32,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(pixel*32))+chunk(b'IEND',b'')
    if key.startswith('audio'):
        stream=io.BytesIO()
        with wave.open(stream,'wb') as w: w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(b'\x00\x00'*8000)
        return stream.getvalue()+(b'v2' if key.endswith('v2') else b'')
    if key=='caption-v1': return 'WEBVTT\n\n00:00.000 --> 00:01.000\n欢迎了解本地游。\n'.encode()
    return packed({'说明.txt':'合成宣传可选说明'.encode(),'manifest.json':dump({'files':['说明.txt']}).encode()})
class App(Application):
    def __init__(self): super().__init__();self.leases={}
    def handle(self,h):
        p=h.path_only
        if p=='/': return self.document(h,'宣传素材来源','<a href="/catalog">发布目录</a>')
        if p=='/catalog': return self.emit(h,{'now':self.stage,'publications':self.seed['publications'],'rights':self.data('rights'),'components':self.seed['components']})
        if p.startswith('/lease/'):
            key=p.split('/')[-1];data=asset(key,self.data('generation'));token=secrets.token_hex(8)
            self.leases[token]={'key':key,'generation':self.data('generation'),'stage':self.stage}
            return self.emit(h,{'component':key,'url':'/raw/'+key+'?token='+token,'etag':digest(data),'sha256':digest(data),'size':len(data),'expires_at_stage':self.stage+1})
        if p.startswith('/raw/'):
            token=h.query['token'];lease=self.leases[token]
            if lease['stage']!=self.stage: return self.emit(h,{'error':'lease_expired'},403)
            key=p.split('/')[-1]
            if lease['key']!=key: return self.emit(h,{'error':'scope'},403)
            data=asset(key,self.data('generation'));etag='"'+digest(data)+'"'
            if h.headers.get('If-Match') and h.headers['If-Match']!=etag: return self.emit(h,{'error':'changed'},412)
            headers={'ETag':etag,'Accept-Ranges':'bytes'};status=200
            if h.headers.get('Range') and not self.data('ignore_range'):
                start,end=h.headers['Range'].removeprefix('bytes=').split('-');start=int(start);end=int(end) if end else len(data)-1
                if start>=len(data): return h.send(b'','application/octet-stream',416,{'Content-Range':'bytes */'+str(len(data))})
                end=min(end,len(data)-1);headers['Content-Range']=f'bytes {start}-{end}/{len(data)}';data=data[start:end+1];status=206
            return h.send(data,'application/octet-stream',status,headers)
        if p in ['/channel/deliver','/channel/stop']:
            bucket='deliveries' if p.endswith('deliver') else 'stops'
            if h.command=='POST':
                item=self.record(bucket,h.body['reference'],h.body)
                if h.body.get('lose_response'): return h.send(b'','text/plain',503)
            for item in self.remote.get('stops',{}).values(): item['state']='confirmed' if self.data('stop_confirm') else 'pending'
            return self.emit(h,self.remote.get(bucket,{}))
        return self.emit(h,{'error':'not_found'},404)
if __name__=='__main__': main(App())
