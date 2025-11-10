#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
照片批量添加拍摄时间水印脚本
功能：
1. 批量读取文件夹内的照片文件
2. 获取照片文件的拍摄时间
3. 将拍摄时间转换成水印，贴在照片的右下角
4. 将添加水印后的照片保存到 mask 文件夹内
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont
from PIL.ExifTags import TAGS
from datetime import datetime
import argparse

def get_photo_taken_time(image_path):
    """
    获取照片的拍摄时间
    优先从EXIF数据中获取，如果没有则使用文件修改时间
    """
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()
        
        if exif_data:
            for tag, value in exif_data.items():
                if TAGS.get(tag) == 'DateTimeOriginal':
                    # 解析EXIF中的拍摄时间
                    return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
    
    except Exception as e:
        print(f"读取EXIF数据失败: {e}")
    
    # 如果无法从EXIF获取，使用文件修改时间
    try:
        file_time = os.path.getmtime(image_path)
        return datetime.fromtimestamp(file_time)
    except Exception as e:
        print(f"获取文件时间失败: {e}")
        return datetime.now()

def add_watermark(image_path, output_path, font_path=None):
    """
    为照片添加拍摄时间水印
    
    Args:
        image_path (str): 输入图片路径
        output_path (str): 输出图片路径
        font_path (str, optional): 字体文件路径
    
    Returns:
        bool: 处理成功返回True，失败返回False
    """
    try:
        # 打开图片，保持原始属性
        with Image.open(image_path) as image:
            # 保存原始信息
            original_format = image.format
            original_info = image.info.copy()
            original_exif = original_info.get('exif', b'')
            
            # 获取拍摄时间和水印文本
            taken_time = get_photo_taken_time(image_path)
            watermark_text = taken_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # 获取图片尺寸
            img_width, img_height = image.size
            
            # 计算字体大小
            font_size = _calculate_optimal_font_size(watermark_text, img_width, img_height)
            
            # 加载字体
            font = _load_font(font_path, font_size)
            # 计算水印位置
            position = _calculate_watermark_position(image, watermark_text, font)
            
            # 添加水印（考虑EXIF方向）
            _add_text_with_orientation(image, watermark_text, font, position)
            
            # 保存图片，保留所有原始信息
            _save_image_with_metadata(image, output_path, original_format, original_info, original_exif)
            
            print(f"✓ 已处理: {os.path.basename(image_path)} -> {watermark_text} (字体大小: {font_size}px)")
            return True
            
    except Exception as e:
        print(f"✗ 处理失败 {os.path.basename(image_path)}: {e}")
        return False


def _calculate_optimal_font_size(text, img_width, img_height):
    """
    计算最优字体大小，使文字面积约占图片面积的3%
    
    Args:
        text (str): 水印文本
        img_width (int): 图片宽度
        img_height (int): 图片高度
    
    Returns:
        int: 计算得出的字体大小
    """
    img_area = img_width * img_height
    target_text_area = img_area * 0.03
    
    # 经验公式：考虑字符宽高比和文字密度
    char_width_ratio = 0.6  # 字符平均宽高比
    text_density_factor = 2  # 文字密度因子
    
    font_size = int((target_text_area / (len(text) * char_width_ratio * text_density_factor)) ** 0.5)
    
    # 限制字体大小在合理范围内
    min_font_size = 20
    max_font_size = min(img_width, img_height) // 10
    
    return max(min_font_size, min(font_size, max_font_size))


def _load_font(font_path, font_size):
    """
    加载字体，支持多种回退选项
    
    Args:
        font_path (str): 字体文件路径
        font_size (int): 字体大小
    
    Returns:
        ImageFont.FreeTypeFont: 加载的字体对象
    """
    # 字体优先级列表
    font_candidates = []
    
    if font_path and os.path.exists(font_path):
        font_candidates.append(font_path)
    
    # 常见系统字体
    system_fonts = [
        "arial.ttf",
        "times.ttf", 
        "calibri.ttf",
        "verdana.ttf",
        "tahoma.ttf"
    ]
    
    font_candidates.extend(system_fonts)
    
    # 尝试加载字体
    for font_candidate in font_candidates:
        try:
            return ImageFont.truetype(font_candidate, font_size)
        except (IOError, OSError):
            continue
    
    # 最后回退到默认字体
    return ImageFont.load_default()

def _calculate_watermark_position(image, text, font):
    """
    计算水印位置（右下角），确保竖屏照片水印位置正确且不旋转
    
    Args:
        image (PIL.Image): 图片对象
        text (str): 水印文本
        font (ImageFont.FreeTypeFont): 字体对象
    
    Returns:
        tuple: (x, y) 坐标
    """
    draw = ImageDraw.Draw(image)
    img_width, img_height = image.size
    
    # 获取EXIF方向信息并计算实际显示尺寸
    actual_width, actual_height = _get_actual_dimensions(image)
    
    # 计算文字尺寸
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # 计算边距（根据实际显示尺寸自适应）
    margin = max(10, min(actual_width, actual_height) // 100)
    
    # 右下角位置计算（基于实际显示尺寸）
    # 但是要在当前图片尺寸上绘制，所以需要根据方向调整坐标
    x, y = _adjust_position_for_orientation(
        img_width, img_height, actual_width, actual_height,
        text_width, text_height, margin, image
    )
    
    # 确保水印完全在图片内
    if x < 0:
        x = max(0, img_width // 20)
    if y < 0:
        y = max(0, img_height // 20)
    
    # 调试信息（可以取消注释来查看计算过程）
    # print(f"图片尺寸: {img_width}x{img_height}, 实际显示尺寸: {actual_width}x{actual_height}")
    # print(f"文字尺寸: {text_width}x{text_height}, 计算位置: ({x}, {y})")
    
    return (x, y)


def _get_actual_dimensions(image):
    """
    根据EXIF方向标签获取图片的实际显示尺寸
    
    Args:
        image (PIL.Image): 图片对象
    
    Returns:
        tuple: (actual_width, actual_height) 实际显示尺寸
    """
    img_width, img_height = image.size
    
    try:
        exif_data = image._getexif()
        if exif_data:
            # EXIF方向标签 (0x0112 = 274)
            orientation = exif_data.get(274, 1)
            
            # 根据方向标签调整尺寸
            if orientation == 3:  # 旋转180度
                return img_width, img_height
            elif orientation == 6:  # 顺时针旋转90度
                return img_height, img_width
            elif orientation == 8:  # 逆时针旋转90度
                return img_height, img_width
            elif orientation == 5:  # 逆时针旋转90度 + 水平翻转
                return img_height, img_width
            elif orientation == 7:  # 顺时针旋转90度 + 水平翻转
                return img_height, img_width
            # orientation 1, 2, 4 不需要交换宽高
            # 1: 正常
            # 2: 水平翻转
            # 4: 垂直翻转
    
    except Exception:
        pass
    
    # 默认返回原始尺寸
    return img_width, img_height


def _adjust_position_for_orientation(img_width, img_height, actual_width, actual_height, 
                                  text_width, text_height, margin, image):
    """
    根据EXIF方向调整水印位置坐标
    
    Args:
        img_width, img_height: 当前图片尺寸
        actual_width, actual_height: 实际显示尺寸
        text_width, text_height: 文字尺寸
        margin: 边距
        image: 图片对象
    
    Returns:
        tuple: (x, y) 调整后的坐标
    """
    try:
        exif_data = image._getexif()
        if exif_data:
            orientation = exif_data.get(274, 1)
            
            # 计算在实际显示尺寸中的右下角位置
            actual_x = actual_width - text_width - margin
            actual_y = actual_height - text_height - margin
            
            # 根据方向转换坐标
            if orientation == 1:  # 正常
                return actual_x, actual_y
            elif orientation == 2:  # 水平翻转
                return img_width - actual_x - text_width, actual_y
            elif orientation == 3:  # 旋转180度
                return img_width - actual_x - text_width, img_height - actual_y - text_height
            elif orientation == 4:  # 垂直翻转
                return actual_x, img_height - actual_y - text_height
            elif orientation == 5:  # 逆时针旋转90度 + 水平翻转
                # 实际: (actual_x, actual_y) -> 当前: (img_height - actual_y - text_height, actual_x)
                return img_height - actual_y - text_height, actual_x
            elif orientation == 6:  # 顺时针旋转90度
                # 实际: (actual_x, actual_y) -> 当前: (actual_y, img_width - actual_x - text_width)
                return actual_y, img_width - actual_x - text_width
            elif orientation == 7:  # 顺时针旋转90度 + 水平翻转
                # 实际: (actual_x, actual_y) -> 当前: (actual_y, img_width - (actual_width - actual_x - text_width))
                return actual_y, img_width - (actual_width - actual_x - text_width)
            elif orientation == 8:  # 逆时针旋转90度
                # 实际: (actual_x, actual_y) -> 当前: (img_height - actual_x - text_width, actual_y)
                return img_height - actual_x - text_width, actual_y
    
    except Exception:
        pass
    
    # 默认计算（无EXIF或出错时）
    return img_width - text_width - margin, img_height - text_height - margin


def _add_text_with_orientation(image, text, font, position):
    """
    根据EXIF方向添加文字，确保文字方向正确
    
    Args:
        image (PIL.Image): 图片对象
        text (str): 水印文本
        font (ImageFont.FreeTypeFont): 字体对象
        position (tuple): 文字位置 (x, y)
    """
    draw = ImageDraw.Draw(image)
    
    try:
        exif_data = image._getexif()
        if exif_data:
            orientation = exif_data.get(274, 1)
            
            # 根据EXIF方向调整文字
            # 注意：EXIF方向标签表示的是相机拍摄时的方向
            # 我们需要反向旋转文字来抵消这个方向变化
            if orientation == 3:  # 旋转180度
                # 直接绘制文字然后旋转整个图像区域
                temp_img = Image.new('RGBA', image.size, (0, 0, 0, 0))
                temp_draw = ImageDraw.Draw(temp_img)
                temp_draw.text(position, text, font=font, fill="#FFD700")
                # 旋转180度
                rotated_text = temp_img.rotate(180, expand=False)
                image.paste(rotated_text, (0, 0), rotated_text)
            elif orientation == 6:  # 顺时针旋转90度
                # 直接绘制文字然后旋转整个图像区域
                temp_img = Image.new('RGBA', image.size, (0, 0, 0, 0))
                temp_draw = ImageDraw.Draw(temp_img)
                temp_draw.text(position, text, font=font, fill="#FFD700")
                # 逆时针旋转90度
                rotated_text = temp_img.rotate(90, expand=False)
                image.paste(rotated_text, (0, 0), rotated_text)
            elif orientation == 8:  # 逆时针旋转90度
                # 直接绘制文字然后旋转整个图像区域
                temp_img = Image.new('RGBA', image.size, (0, 0, 0, 0))
                temp_draw = ImageDraw.Draw(temp_img)
                temp_draw.text(position, text, font=font, fill="#FFD700")
                # 顺时针旋转90度
                rotated_text = temp_img.rotate(-90, expand=False)
                image.paste(rotated_text, (0, 0), rotated_text)
            else:
                # 其他方向（1,2,4,5,7）直接绘制文字
                draw.text(position, text, font=font, fill="#FFD700")
        else:
            # 无EXIF信息，直接绘制
            draw.text(position, text, font=font, fill="#FFD700")
    
    except Exception:
        # 出错时直接绘制
        draw.text(position, text, font=font, fill="#FFD700")


def _create_rotated_text(text, font, angle):
    """
    创建旋转文字的尺寸估算
    
    Args:
        text (str): 文本内容
        font (ImageFont.FreeTypeFont): 字体对象
        angle (int): 旋转角度
    
    Returns:
        tuple: (width, height) 旋转后的尺寸
    """
    # 创建临时图像来测量文字尺寸
    temp_img = Image.new('RGB', (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    bbox = temp_draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # 估算旋转后的尺寸（简化计算）
    import math
    angle_rad = math.radians(abs(angle))
    rotated_width = int(text_width * abs(math.cos(angle_rad)) + text_height * abs(math.sin(angle_rad)))
    rotated_height = int(text_width * abs(math.sin(angle_rad)) + text_height * abs(math.cos(angle_rad)))
    
    return (rotated_width, rotated_height)


def _save_image_with_metadata(image, output_path, original_format, original_info, original_exif):
    """
    保存图片，保留所有原始元数据
    
    Args:
        image (PIL.Image): 图片对象
        output_path (str): 输出路径
        original_format (str): 原始格式
        original_info (dict): 原始信息字典
        original_exif (bytes): 原始EXIF数据
    """
    # 准备保存参数
    save_kwargs = {}
    
    # 保留EXIF信息
    if original_exif:
        save_kwargs['exif'] = original_exif
    
    # 保留其他元数据
    for key, value in original_info.items():
        if key not in ['exif'] and key not in save_kwargs:
            save_kwargs[key] = value
    
    # 确定保存格式
    if original_format:
        save_kwargs['format'] = original_format
    else:
        # 根据文件扩展名推断格式
        ext = os.path.splitext(output_path)[1].lower()
        format_map = {
            '.jpg': 'JPEG',
            '.jpeg': 'JPEG', 
            '.png': 'PNG',
            '.bmp': 'BMP',
            '.tiff': 'TIFF',
            '.tif': 'TIFF'
        }
        save_kwargs['format'] = format_map.get(ext, 'JPEG')
    
    # 保存图片（不进行压缩）
    image.save(output_path, **save_kwargs)

def process_folder(input_folder, font_path=None):
    """
    处理文件夹中的所有照片
    """
    # 支持的图片格式
    supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif')
    
    # 创建输出文件夹
    output_folder = os.path.join(input_folder, 'mask')
    os.makedirs(output_folder, exist_ok=True)
    
    print(f"开始处理文件夹: {input_folder}")
    print(f"输出文件夹: {output_folder}")
    print("-" * 50)
    
    processed_count = 0
    total_count = 0
    
    # 遍历文件夹中的所有文件
    for filename in os.listdir(input_folder):
        if filename.lower().endswith(supported_formats):
            total_count += 1
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, f"watermarked_{filename}")
            
            if add_watermark(input_path, output_path, font_path):
                processed_count += 1
    
    print("-" * 50)
    print(f"处理完成！共处理 {processed_count} 张照片，总计 {total_count} 张图片文件")

def main():
    parser = argparse.ArgumentParser(description='为照片批量添加拍摄时间水印')
    parser.add_argument('--input_folder', required=True, help='包含照片的输入文件夹路径')
    parser.add_argument('--font', help='字体文件路径（DBLCDTempBlack字体）')
    
    args = parser.parse_args()
    
    # 检查输入文件夹是否存在
    if not os.path.exists(args.input_folder):
        print(f"错误：文件夹 '{args.input_folder}' 不存在")
        sys.exit(1)
    
    # 检查是否是文件夹
    if not os.path.isdir(args.input_folder):
        print(f"错误：'{args.input_folder}' 不是文件夹")
        sys.exit(1)
    
    # 处理文件夹
    process_folder(args.input_folder, args.font)

if __name__ == "__main__":
    main()