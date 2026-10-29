import base64,io
from PIL import Image
from .test_studio import StudioTests
from . import product_images as images
class ImageTests(StudioTests):
 def payload(self):
  b=io.BytesIO();Image.new('RGB',(16,20),'white').save(b,format='PNG')
  return {'product_id':self.kb()['product_id'],'filename':'测试.png','content_base64':base64.b64encode(b.getvalue()).decode()}
 def test_original_roundtrip_and_metadata(self):
  p=self.payload();r=images.upload(p);raw,mime=images.read(r['image_id']);self.assertEqual(raw,base64.b64decode(p['content_base64']));self.assertEqual(mime,'image/png');self.assertEqual(images.images()[0]['width'],16)
 def test_invalid_image_and_missing_product_are_rejected(self):
  p=self.payload();p['content_base64']=base64.b64encode(b'<script>not an image</script>').decode()
  with self.assertRaises(ValueError):images.upload(p)
  p=self.payload();p.pop('product_id')
  with self.assertRaises(ValueError):images.upload(p)
  with self.assertRaises(ValueError):images.read('../../secret')
