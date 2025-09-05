from utils.image_utils import optimize_image


class TestImageUtils:
    def test_optimize_image(self):
        from PIL import Image
        import io
        img = Image.new('RGB', (2000, 2000), color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        original_bytes = buffer.getvalue()
        optimized = optimize_image(original_bytes, max_size=1024)
        optimized_img = Image.open(io.BytesIO(optimized))
        assert max(optimized_img.size) <= 1024
        assert optimized_img.format == 'JPEG'

    def test_optimize_image_rgba_to_rgb(self):
        from PIL import Image
        import io
        img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        rgba_bytes = buffer.getvalue()
        optimized = optimize_image(rgba_bytes)
        optimized_img = Image.open(io.BytesIO(optimized))
        assert optimized_img.mode == 'RGB'
