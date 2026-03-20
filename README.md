# WindTranslator

将英文 EPUB 电子书翻译成中文并输出为 PDF 文件的命令行工具，基于大语言模型（LLM）提供专业翻译质量。

```
# 使用方法：


# 预览章节列表（不翻译）
./epub-translator your_book.epub --list
./epub-translator your_book.pdf --list

# 翻译全书
./epub-translator your_book.epub
./epub-translator your_book.pdf

# 只翻译第 1-5 章
./epub-translator your_book.epub --chapters 1-5

# 指定输出路径
./epub-translator your_book.epub -o ~/Desktop/output_zh.pdf

# 临时覆盖 API Key
./epub-translator your_book.epub --api-key sk-xxx

# 调试模式（输出详细日志）
./epub-translator your_book.epub -v
从任意目录调用（可选）： 把项目路径加入 ~/.zshrc：


echo 'export PATH="$PATH:/Users/xiaoguangyang/Downloads/res/WindTranslator"' >> ~/.zshrc
source ~/.zshrc

# 之后可在任意目录直接使用
epub-translator your_book.epub --list
```