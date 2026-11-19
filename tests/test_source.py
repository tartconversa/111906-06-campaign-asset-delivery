"""范围传输、换签身份与渠道单站回执检查。"""
from support import *
class Protocol(SourceCase):
    def test_range_etag_and_remote_stop(self):
        lease=self.value('/lease/cover');status,headers,data=self.request(lease['url'],headers={'Range':'bytes=0-9'});self.assertEqual(status,206);self.assertEqual(len(data),10);self.assertTrue(data.startswith(b'\x89PNG'));self.assertIn('Content-Range',headers)
        self.control(1);self.assertEqual(self.request(lease['url'])[0],403);new=self.value('/lease/cover');self.assertNotEqual(new['etag'],lease['etag']);self.assertEqual(self.request(new['url'],headers={'If-Match':'"'+lease['etag']+'"'})[0],412)
        self.control(2);lease=self.value('/lease/cover');status,_,data=self.request(lease['url'],headers={'Range':'bytes=2-3'});self.assertEqual(status,200);self.assertEqual(hashlib.sha256(data).hexdigest(),lease['sha256'])
        self.request('/channel/stop',{'reference':'source-check','delivery_reference':'raw','reason':'source transport probe'});self.assertEqual(self.value('/channel/stop')['source-check']['state'],'confirmed')
