"""
测试图片提取功能
"""

import sys
import codecs

# Windows UTF-8 兼容性
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from crawler.doc_analyzer import DocumentAnalyzer

def test_extract_images():
    """测试 _extract_images 方法"""
    analyzer = DocumentAnalyzer()

    # 测试用例 1: 标准 Markdown 图片
    content1 = "这是一段文字 ![架构图](images/arch.png) 继续文字"
    images1 = analyzer._extract_images(content1)
    assert len(images1) == 1
    assert images1[0]['alt'] == '架构图'
    assert images1[0]['path'] == 'images/arch.png'
    print("✓ 测试 1 通过: 标准图片引用")

    # 测试用例 2: 无 alt 文本
    content2 = "![](images/diagram.jpg)"
    images2 = analyzer._extract_images(content2)
    assert len(images2) == 1
    assert images2[0]['alt'] == '(无描述)'
    assert images2[0]['path'] == 'images/diagram.jpg'
    print("✓ 测试 2 通过: 无 alt 文本")

    # 测试用例 3: 多个图片
    content3 = """
    ![图1](img1.png)
    一些文字
    ![图2](img2.jpg)
    ![图3](img3.svg)
    """
    images3 = analyzer._extract_images(content3)
    assert len(images3) == 3
    assert images3[0]['alt'] == '图1'
    assert images3[1]['alt'] == '图2'
    assert images3[2]['alt'] == '图3'
    print("✓ 测试 3 通过: 多个图片")

    # 测试用例 4: 无图片
    content4 = "这是一段没有图片的文字"
    images4 = analyzer._extract_images(content4)
    assert len(images4) == 0
    print("✓ 测试 4 通过: 无图片")

    # 测试用例 5: 带空格的 alt 文本
    content5 = "![  系统架构图  ](  /path/to/image.png  )"
    images5 = analyzer._extract_images(content5)
    assert len(images5) == 1
    assert images5[0]['alt'] == '系统架构图'
    assert images5[0]['path'] == '/path/to/image.png'
    print("✓ 测试 5 通过: 带空格的引用")

    print("\n✅ 所有测试通过!")

if __name__ == '__main__':
    test_extract_images()
