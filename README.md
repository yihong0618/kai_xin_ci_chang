# cichang_remember
开心词场帮助程序
![image](https://user-images.githubusercontent.com/15976103/107328965-756e8180-6aea-11eb-9fff-6717094d74fa.png)

## PS
- 这个项目不做解答和额外内容
- 不接受 feature 的 PR

## USE
1. python3.6 or higher
2. pip install -r requirements.txt
3. python cichang.py 'your user name' 'your password'
4. 如果你想下载小D词典的单词加上命令 -xd `python cichang.py 'your user name' 'your password' -xd`

## INFO
- 所有文件存在 `FILES_OUT` 里
- files 中你的内容是加密的
- 我解密了一些你需要的内容默认是 `my_learning_book.csv`
- 默认下载你正在学的书，有能力的同学可以根据代码更改（已经写好注释）
- csv 中对应的 id 能在下载的 mp3 中找到，有兴趣的同学可以用 ffmpeg 生成自己的 mp3
