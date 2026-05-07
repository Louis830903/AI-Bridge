"""
Office 领域意图模式 — 12 个模式
覆盖 Word、Excel、PPT 以及通用文档操作
"""

from aibridge.core.intent_pattern import IntentPattern, Slot, SlotType

OFFICE_PATTERNS = [
    # Word
    IntentPattern(
        id="office.create_doc", domain="office",
        patterns=["创建一个文档", "新建{类型:string}文档"],
        description="创建新文档",
        slots=[Slot("类型", SlotType.STRING, default="word", description="文档类型(word/excel/ppt)")],
        examples=["创建一个文档", "新建word文档"],
    ),
    IntentPattern(
        id="office.open_doc", domain="office",
        patterns=["打开{文件:path}", "编辑{文件:path}"],
        description="打开并编辑文档",
        slots=[Slot("文件", SlotType.PATH, description="文档文件路径")],
        examples=["打开report.docx", "编辑表格.xlsx"],
    ),
    IntentPattern(
        id="office.export_pdf", domain="office",
        patterns=["把{文件:path}导出为PDF", "{文件:path}转PDF"],
        description="将文档导出为PDF格式",
        slots=[Slot("文件", SlotType.PATH, description="源文件路径")],
        examples=["把report.docx导出为PDF", "表格.xlsx转PDF"],
    ),
    # Excel
    IntentPattern(
        id="office.excel_sum", domain="office",
        patterns=["求{范围:string}的和", "计算{范围:string}总和"],
        description="计算指定范围的总和",
        slots=[Slot("范围", SlotType.STRING, description="单元格范围如A1:B10")],
        examples=["求A1:A10的和", "计算B2:D20总和"],
    ),
    IntentPattern(
        id="office.excel_chart", domain="office",
        patterns=["用{范围:string}生成{图表类型:string}图",
                 "根据{范围:string}画{图表类型:string}"],
        description="根据数据生成图表",
        slots=[
            Slot("范围", SlotType.STRING, description="数据范围"),
            Slot("图表类型", SlotType.STRING, description="图表类型",
                 enum_values=["柱状", "折线", "饼", "散点"]),
        ],
        examples=["用A1:B10生成柱状图", "根据A1:D20画折线"],
    ),
    IntentPattern(
        id="office.excel_pivot", domain="office",
        patterns=["以{行:string}为行{值:string}为值创建数据透视表"],
        description="创建数据透视表",
        slots=[
            Slot("行", SlotType.STRING, description="行标签字段"),
            Slot("值", SlotType.STRING, description="值字段"),
        ],
        examples=["以月份为行销售额为值创建数据透视表", "以产品为行利润为值创建数据透视表"],
    ),
    # PPT
    IntentPattern(
        id="office.ppt_create", domain="office",
        patterns=["生成{主题:string}的PPT", "创建关于{主题:string}的演示文稿"],
        description="创建PPT演示文稿",
        slots=[Slot("主题", SlotType.STRING, description="演示文稿主题")],
        examples=["生成项目报告的PPT", "创建关于人工智能的演示文稿"],
    ),
    IntentPattern(
        id="office.ppt_add_slide", domain="office",
        patterns=["添加一张{布局:string}幻灯片"],
        description="添加幻灯片页面",
        slots=[Slot("布局", SlotType.STRING, description="页面布局类型",
                   enum_values=["标题", "内容", "空白", "两栏"])],
        examples=["添加一张标题幻灯片", "添加一张内容幻灯片"],
    ),
    # 通用
    IntentPattern(
        id="office.extract_tables", domain="office",
        patterns=["提取{文件:path}中的表格", "从{文件:path}导出表格数据"],
        description="从文档中提取表格数据",
        slots=[Slot("文件", SlotType.PATH, description="文档文件路径")],
        examples=["提取report.docx中的表格", "从data.xlsx导出表格数据"],
    ),
    IntentPattern(
        id="office.format", domain="office",
        patterns=["格式化{文件:path}", "美化{文件:path}的排版"],
        description="美化文档排版格式",
        slots=[Slot("文件", SlotType.PATH, description="文档文件路径")],
        examples=["格式化report.docx", "美化论文.docx的排版"],
    ),
    IntentPattern(
        id="office.merge", domain="office",
        patterns=["合并{文件列表:string}到{目标:string}"],
        description="合并多个文档/表格到一个文件",
        slots=[
            Slot("文件列表", SlotType.STRING, description="逗号分隔的文件列表"),
            Slot("目标", SlotType.STRING, description="目标描述"),
        ],
        examples=["合并a.docx,b.docx到一个文档", "合并sheet1.xlsx,sheet2.xlsx到汇总表"],
    ),
    IntentPattern(
        id="office.mail_merge", domain="office",
        patterns=["用{数据源:path}填充{模板:path}", "邮件合并"],
        description="邮件合并——用数据源填充模板",
        slots=[
            Slot("数据源", SlotType.PATH, description="数据源文件路径"),
            Slot("模板", SlotType.PATH, description="模板文件路径"),
        ],
        examples=["用contacts.xlsx填充template.docx", "邮件合并"],
    ),
]
