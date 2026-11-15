"""HTML 清洗差异报表。

在不改变 ``bleach.clean()`` 行为的前提下，为批量清洗补充留痕能力：
每条片段清洗前后的对照（``items``）以及整批被中和的危险标签计数
（``tags``），便于运营回答"这批内容清掉了什么"。

设计说明：

* ``after`` 直接取公开 API ``bleach.clean()`` 默认参数的结果，与入库
  清洗完全一致，本模块不复制任何清洗逻辑。
* 默认配置下 ``clean()`` 对不在白名单内的普通标签（如 ``<p>``）只做
  转义、不删内容，文本语义未变，因此不计入"被移除标签"，对应片段
  标记为 ``changed=False``。
* ``tags`` 只统计可执行脚本、嵌入外部资源或改变文档级行为的主动
  内容类标签（见 :data:`DANGEROUS_TAGS`）；这类标签被 ``clean()``
  中和（转义或剥离）即视为移除。按元素出现次数计数，标签名统一
  为小写。
"""

from bleach import clean
from bleach import html5lib_shim


#: 主动内容类标签：可执行脚本、嵌入外部资源/插件或改变文档级行为。
#: 普通内容/排版标签（p、div、span、img 等）不在其中——它们被
#: 转义并不改变文本语义，事件属性等属性级风险由 clean() 另行剥离。
DANGEROUS_TAGS = frozenset(
    (
        "applet",
        "audio",
        "base",
        "canvas",
        "embed",
        "frame",
        "frameset",
        "iframe",
        "link",
        "math",
        "meta",
        "noscript",
        "object",
        "param",
        "script",
        "source",
        "style",
        "svg",
        "template",
        "track",
        "video",
    )
)

#: 每个元素只计一次：开标签与自闭合标签计数，闭合标签不重复计。
_COUNTED_TOKEN_TYPES = frozenset(("StartTag", "EmptyTag"))


class CleanReport:
    """清洗报表。

    :ivar items: 逐条对照，每项为含 ``index``、``before``、``after``、
        ``changed`` 的字典
    :ivar tags: 整批片段中被移除的危险标签 -> 出现次数
    """

    __slots__ = ("items", "tags")

    def __init__(self, items, tags):
        self.items = items
        self.tags = tags

    def __repr__(self):
        return f"CleanReport(items={self.items!r}, tags={self.tags!r})"


def _count_dangerous_tags(text):
    """解析片段并统计其中危险标签的出现次数。

    使用 ``tags=None`` 的解析器做只读观察：不剥离、不转义任何标签，
    因此对清洗路径没有影响。解析器持有内部状态，每次调用新建实例。

    :arg str text: 原始 HTML 片段
    :returns: ``{标签名: 次数}``，标签名为小写
    """
    parser = html5lib_shim.BleachHTMLParser(
        tags=None,
        strip=False,
        consume_entities=False,
        namespaceHTMLElements=False,
    )
    walker = html5lib_shim.getTreeWalker("etree")

    counts = {}
    for token in walker(parser.parseFragment(text)):
        if token["type"] not in _COUNTED_TOKEN_TYPES:
            continue
        name = token["name"]
        if name in DANGEROUS_TAGS:
            counts[name] = counts.get(name, 0) + 1
    return counts


def clean_report(snippets):
    """批量清洗 HTML 片段并产出差异报表。

    :arg snippets: 待清洗的 HTML 片段字符串序列
    :returns: :class:`CleanReport`；``items`` 按入参顺序给出逐条对照
        （``index``、``before``、``after``、``changed``），``tags``
        汇总整批被移除的危险标签及次数
    :raises TypeError: 片段不是字符串时，由底层 ``bleach.clean()`` 抛出
    """
    items = []
    tags_total = {}

    for index, before in enumerate(snippets):
        after = clean(before)
        removed = _count_dangerous_tags(before)

        for name, count in removed.items():
            tags_total[name] = tags_total.get(name, 0) + count

        items.append(
            {
                "index": index,
                "before": before,
                "after": after,
                "changed": bool(removed),
            }
        )

    return CleanReport(items=items, tags=tags_total)
