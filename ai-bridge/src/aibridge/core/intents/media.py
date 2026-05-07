"""
Media 领域意图模式 — 18 个模式
覆盖视频/音频转换、压缩、裁剪、提取、水印、拼接、调帧率、GIF等
"""

from aibridge.core.intent_pattern import IntentPattern, Slot, SlotType

MEDIA_FORMATS = ["mp4", "avi", "mkv", "mov", "gif", "webm", "mp3", "wav", "flac", "ogg"]

MEDIA_PATTERNS = [
    IntentPattern(
        id="media.convert", domain="media",
        patterns=["把{输入:path}转成{格式:format}", "{输入:path}转换为{格式:format}"],
        description="视频/音频格式转换",
        slots=[
            Slot("输入", SlotType.PATH, description="输入文件路径"),
            Slot("格式", SlotType.FORMAT, description="目标格式", enum_values=MEDIA_FORMATS),
        ],
        examples=["把video.mp4转成gif", "audio.wav转换为mp3"],
    ),
    IntentPattern(
        id="media.compress", domain="media",
        patterns=["压缩{文件:path}到{大小:integer}MB以内", "把{文件:path}压到{大小:integer}M"],
        description="压缩视频文件到指定大小",
        slots=[
            Slot("文件", SlotType.PATH, description="输入文件路径"),
            Slot("大小", SlotType.INTEGER, description="目标大小(MB)"),
        ],
        examples=["压缩movie.mp4到50MB以内", "把video.mp4压到10M"],
    ),
    IntentPattern(
        id="media.trim", domain="media",
        patterns=["裁剪{文件:path}从{开始:duration}到{结束:duration}",
                 "截取{文件:path}的{开始:duration}到{结束:duration}"],
        description="裁剪视频片段",
        slots=[
            Slot("文件", SlotType.PATH, description="输入文件路径"),
            Slot("开始", SlotType.DURATION, description="开始时间"),
            Slot("结束", SlotType.DURATION, description="结束时间"),
        ],
        examples=["裁剪clip.mp4从10s到30s", "截取movie.mp4的1:00到2:30"],
    ),
    IntentPattern(
        id="media.extract_audio", domain="media",
        patterns=["提取{视频:path}的音频", "从{视频:path}分离音轨"],
        description="从视频中提取音频",
        slots=[Slot("视频", SlotType.PATH, description="视频文件路径")],
        examples=["提取video.mp4的音频", "从movie.mp4分离音轨"],
    ),
    IntentPattern(
        id="media.watermark", domain="media",
        patterns=["给{文件:path}加水印{水印:string}"],
        description="给视频添加水印",
        slots=[
            Slot("文件", SlotType.PATH, description="视频文件路径"),
            Slot("水印", SlotType.STRING, description="水印文字"),
        ],
        examples=["给video.mp4加水印MyBrand", "给movie.mp4加水印Copyright"],
    ),
    IntentPattern(
        id="media.concat", domain="media",
        patterns=["拼接{文件列表:string}", "合并{文件列表:string}为一个视频"],
        description="拼接多个视频文件为一个",
        slots=[Slot("文件列表", SlotType.STRING, description="用逗号分隔的文件列表")],
        examples=["拼接clip1.mp4,clip2.mp4", "合并part1.mp4,part2.mp4为一个视频"],
    ),
    IntentPattern(
        id="media.resize", domain="media",
        patterns=["调整{文件:path}分辨率为{宽:integer}x{高:integer}"],
        description="调整视频分辨率",
        slots=[
            Slot("文件", SlotType.PATH, description="视频文件路径"),
            Slot("宽", SlotType.INTEGER, description="目标宽度(像素)"),
            Slot("高", SlotType.INTEGER, description="目标高度(像素)"),
        ],
        examples=["调整video.mp4分辨率为1920x1080", "调整movie.mp4分辨率为1280x720"],
    ),
    IntentPattern(
        id="media.fps_change", domain="media",
        patterns=["把{文件:path}帧率改为{fps:integer}"],
        description="修改视频帧率",
        slots=[
            Slot("文件", SlotType.PATH, description="视频文件路径"),
            Slot("fps", SlotType.INTEGER, description="目标帧率"),
        ],
        examples=["把video.mp4帧率改为30", "把movie.mp4帧率改为60"],
    ),
    IntentPattern(
        id="media.extract_frame", domain="media",
        patterns=["从{文件:path}提取第{帧号:integer}帧",
                 "截取{文件:path}的{时间:duration}处画面"],
        description="从视频中提取单帧画面",
        slots=[
            Slot("文件", SlotType.PATH, description="视频文件路径"),
            Slot("帧号", SlotType.INTEGER, required=False, description="帧序号"),
            Slot("时间", SlotType.DURATION, required=False, description="时间点"),
        ],
        examples=["从video.mp4提取第100帧", "截取movie.mp4的5s处画面"],
    ),
    IntentPattern(
        id="media.gif_from_video", domain="media",
        patterns=["把{视频:path}做成GIF", "{视频:path}转gif", "制作{视频:path}的动态图"],
        description="从视频生成GIF动图",
        slots=[Slot("视频", SlotType.PATH, description="视频文件路径")],
        examples=["把clip.mp4做成GIF", "movie.mp4转gif"],
    ),
    IntentPattern(
        id="media.add_subtitle", domain="media",
        patterns=["给{视频:path}加字幕{字幕:string}"],
        description="给视频添加字幕文本",
        slots=[
            Slot("视频", SlotType.PATH, description="视频文件路径"),
            Slot("字幕", SlotType.STRING, description="字幕内容"),
        ],
        examples=["给video.mp4加字幕Hello World", "给movie.mp4加字幕欢迎收看"],
    ),
    IntentPattern(
        id="media.record_screen", domain="media",
        patterns=["录屏{时长:duration}", "录制屏幕{时长:duration}"],
        description="录制屏幕视频",
        slots=[Slot("时长", SlotType.DURATION, description="录制时长")],
        examples=["录屏30s", "录制屏幕5m"],
    ),
    IntentPattern(
        id="media.screenshot_video", domain="media",
        patterns=["视频{文件:path}截图", "{文件:path}缩略图"],
        description="视频缩略图/截图",
        slots=[Slot("文件", SlotType.PATH, description="视频文件路径")],
        examples=["视频movie.mp4截图", "video.mp4缩略图"],
    ),
    IntentPattern(
        id="media.change_speed", domain="media",
        patterns=["{文件:path}{速度:float}倍速", "把{文件:path}加速{速度:float}倍"],
        description="视频变速播放",
        slots=[
            Slot("文件", SlotType.PATH, description="视频文件路径"),
            Slot("速度", SlotType.FLOAT, description="速度倍率"),
        ],
        examples=["video.mp4 2.0倍速", "把movie.mp4加速1.5倍"],
    ),
    IntentPattern(
        id="media.rotate", domain="media",
        patterns=["旋转{文件:path}{角度:integer}度"],
        description="旋转视频画面",
        slots=[
            Slot("文件", SlotType.PATH, description="视频文件路径"),
            Slot("角度", SlotType.INTEGER, description="旋转角度",
                 enum_values=["90", "180", "270"]),
        ],
        examples=["旋转video.mp4 90度", "旋转movie.mp4 180度"],
    ),
    IntentPattern(
        id="media.denoise", domain="media",
        patterns=["{文件:path}降噪", "给{文件:path}去噪"],
        description="视频降噪处理",
        slots=[Slot("文件", SlotType.PATH, description="视频文件路径")],
        examples=["video.mp4降噪", "给movie.mp4去噪"],
    ),
    IntentPattern(
        id="media.stabilize", domain="media",
        patterns=["稳定{文件:path}", "{文件:path}防抖"],
        description="视频防抖/稳定处理",
        slots=[Slot("文件", SlotType.PATH, description="视频文件路径")],
        examples=["稳定video.mp4", "movie.mp4防抖"],
    ),
    IntentPattern(
        id="media.batch_convert", domain="media",
        patterns=["批量把{目录:path}转成{格式:format}",
                 "把{目录:path}下所有文件转为{格式:format}"],
        description="批量格式转换",
        slots=[
            Slot("目录", SlotType.PATH, description="目标目录路径"),
            Slot("格式", SlotType.FORMAT, description="目标格式", enum_values=MEDIA_FORMATS),
        ],
        examples=["批量把videos/转成mp4", "把input/下所有文件转为mp3"],
    ),
]
