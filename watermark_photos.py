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
    为照片添加拍摄时间水印，处理EXIF方向标签
    
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
            
            # 获取EXIF方向标签
            orientation = _get_exif_orientation(image)
            
            # 根据方向标签调整图片方向以便添加水印
            adjusted_image, rotation_info = _adjust_image_for_watermark(image, orientation)
            
            # 获取拍摄时间和水印文本
            taken_time = get_photo_taken_time(image_path)
            watermark_text = taken_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # 获取调整后的图片尺寸
            adj_width, adj_height = adjusted_image.size
            
            # 计算字体大小
            font_size = _calculate_optimal_font_size(watermark_text, adj_width, adj_height)
            
            # 加载字体
            font = _load_font(font_path, font_size)
            
            # 计算水印位置（基于调整后的图片）
            position = _calculate_watermark_position(adjusted_image, watermark_text, font)
            
            # 添加水印
            draw = ImageDraw.Draw(adjusted_image)
            draw.text(position, watermark_text, font=font, fill="#FFD700")
            
            # 恢复原始方向
            final_image = _restore_original_orientation(adjusted_image, rotation_info)
            
            # 保存图片，保留所有原始信息
            _save_image_with_metadata(final_image, output_path, original_format, original_info, original_exif)
            
            print(f"✓ 已处理: {os.path.basename(image_path)} -> {watermark_text} (字体大小: {font_size}px, 方向: {orientation})")
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
    计算水印位置（右下角）
    
    Args:
        image (PIL.Image): 图片对象
        text (str): 水印文本
        font (ImageFont.FreeTypeFont): 字体对象
    
    Returns:
        tuple: (x, y) 坐标
    """
    draw = ImageDraw.Draw(image)
    img_width, img_height = image.size
    
    # 计算文字尺寸
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # 计算边距（根据图片大小自适应）
    margin = max(20, min(img_width, img_height) // 50)
    
    # 右下角位置
    x = img_width - text_width - margin
    y = img_height - text_height - margin
    
    return (x, y)


def _get_exif_orientation(image):
    """
    获取图片的EXIF方向标签
    
    Args:
        image (PIL.Image): 图片对象
    
    Returns:
        int: 方向标签值 (1-8)
    """
    try:
        exif_data = image._getexif()
        if exif_data:
            for tag, value in exif_data.items():
                if TAGS.get(tag) == 'Orientation':
                    return value
    except Exception:
        pass
    
    return 1  # 默认方向


def _adjust_image_for_watermark(image, orientation):
    """
    根据EXIF方向标签调整图片方向，以便正确添加水印
    
    Args:
        image (PIL.Image): 原始图片对象
        orientation (int): EXIF方向标签
    
    Returns:
        tuple: (调整后的图片, 旋转信息)
    """
    rotation_info = {
        'rotated': False,
        'angle': 0,
        'orientation': orientation
    }
    
    adjusted_image = image.copy()
    
    if orientation == 3:
        # 180度旋转
        adjusted_image = adjusted_image.rotate(180, expand=True)
        rotation_info['rotated'] = True
        rotation_info['angle'] = 180
    elif orientation == 6:
        # 顺时针旋转90度
        adjusted_image = adjusted_image.rotate(-90, expand=True)
        rotation_info['rotated'] = True
        rotation_info['angle'] = -90
    elif orientation == 8:
        # 逆时针旋转90度
        adjusted_image = adjusted_image.rotate(90, expand=True)
        rotation_info['rotated'] = True
        rotation_info['angle'] = 90
    
    return adjusted_image, rotation_info


def _restore_original_orientation(image, rotation_info):
    """
    恢复图片的原始方向
    
    Args:
        image (PIL.Image): 已添加水印的图片
        rotation_info (dict): 旋转信息
    
    Returns:
        PIL.Image: 恢复方向后的图片
    """
    if not rotation_info['rotated']:
        return image
    
    # 恢复到原始方向
    if rotation_info['angle'] == 180:
        return image.rotate(180, expand=True)
    elif rotation_info['angle'] == -90:
        return image.rotate(90, expand=True)
    elif rotation_info['angle'] == 90:
        return image.rotate(-90, expand=True)
    
    return image


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
    parser.add_argument('input_folder', help='包含照片的输入文件夹路径')
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