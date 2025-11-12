# 照片水印工具

这是一个Python脚本，用于批量为照片添加拍摄时间水印。

## 功能特性

1. 批量读取指定文件夹内的照片文件
2. 自动获取照片的拍摄时间（优先从EXIF数据获取）
3. 将拍摄时间作为水印添加到照片右下角
4. 水印使用金色 (#FFD700) 显示
5. 处理后的照片保存到 `mask` 文件夹

## 安装要求

- Python 3.6+
- Pillow 库

## 安装步骤

1. 确保已安装Python 3
2. 安装依赖库：
   ```bash
   pip install -r requirements.txt
   ```

## 使用方法

### 基本用法
```bash
python watermark_photos.py "照片文件夹路径"
```

### 指定字体（可选）
```bash
python watermark_photos.py "照片文件夹路径" --font "字体文件路径"
```

## 支持的图片格式

- JPG/JPEG
- PNG
- BMP
- TIFF
- HEIC/HEIF (需要安装 pillow-heif)

## 输出

- 处理后的照片会保存在输入文件夹下的 `mask` 子文件夹中
- 文件名格式：`watermarked_原文件名`

## 注意事项

1. 脚本会优先从照片的EXIF数据中读取拍摄时间
2. 如果EXIF数据不可用，将使用文件的修改时间
3. 如果没有指定DBLCDTempBlack字体，将使用默认字体
4. 确保有足够的磁盘空间存储处理后的照片

## 示例

```bash
# 处理当前目录下的photos文件夹
python watermark_photos.py ./photos

# 使用自定义字体
python watermark_photos.py ./photos --font ./fonts/DBLCDTempBlack.ttf
```