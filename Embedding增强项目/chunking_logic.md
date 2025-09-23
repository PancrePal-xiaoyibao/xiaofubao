# RAG 文档预处理与分块逻辑说明

## 1. 目标 (Objective)

本预处理脚本旨在将原始文档（如 Markdown 文件）转换为适合检索增强生成（RAG）模型使用的格式。核心目标是创建具有高度语义完整性的文本块（Chunks），同时通过特定标记来优化后续处理流程。

一个好的分块策略能够确保：
-   **语义完整性**：相关联的内容（如标题和其对应的段落、正文和其注释）被保留在同一个块中。
-   **大小适中**：每个块的大小都在一个合理的范围内，以适应大语言模型（LLM）的上下文窗口限制。
-   **结构清晰**：通过统一的标记，使程序能够轻松解析文档结构和内容。

## 2. 核心规则 (Core Rules)

1.  **保留语义单元**：分块的首要原则是保持语义的完整性。标题和其内容、代码和其解释、问题和其答案都应尽可能地被视为一个不可分割的单元。
2.  **标题驱动分块**：文档的章节结构（由 Markdown 的 `#` 标题定义）是分块的主要依据。同时支持中文序号结构（如"一、"、"二、"、"（一）"、"（二）"等）。
3.  **注释不分离**：以"注释"开头的行或段落，应与其前方的正文内容合并在同一个块中，而不是独立成块。
4.  **中文序号语义保持**：中文一级序号（如"一、"、"二、"）与其对应的子序号（如"（一）"、"（二）"）应保持在同一个chunk中，确保章节结构的完整性。
5.  **格式标准化**：所有处理过的文档都遵循统一的格式，包括行号、块边界和文档边界标记。
6.  **索引大小配置**：RAG系统的索引大小设置为1024，确保在向量检索时能够获得最佳的性能和准确性平衡。
7.  **表格完整性保护**：表格内容必须保持完整，不能在分块时被截断。表格与其相关标题应保持在同一chunk中。
8.  **医学文档特殊处理**：对于诊疗指南中的评估体系表格、药物剂量表格等关键信息，应用特殊的保护规则确保其完整性。

### 2.1 中文序号分块逻辑详细规则

基于对实际文档分块问题的分析，特别是针对 `乳腺癌诊疗指南2025_optimized_v2.md` 中发现的分块逻辑错误，制定以下详细的中文序号分块规则：

#### 2.1.1 中文序号层级识别

1. **一级序号（主要章节）**：
   - 格式：`^[一二三四五六七八九十]+、[^（）]*$`
   - 示例：`一、简介`、`二、诊断标准`、`三、治疗方案`、`四、晚期乳腺癌的解救治疗`
   - 分块行为：**触发新chunk创建**

2. **二级序号（子章节）**：
   - 格式：`^（[一二三四五六七八九十]+）[^（）]*$`
   - 示例：`（一）激素受体阳性乳腺癌辅助治疗`、`（二）HER-2阳性晚期乳腺癌解救治疗`
   - 分块行为：**不触发新chunk创建**，应与所属一级序号保持在同一chunk中

3. **三级序号（更细分的子章节）**：
   - 格式：`^[0-9]+\.[0-9]*`、`^[a-zA-Z]\)`等
   - 分块行为：**不触发新chunk创建**

#### 2.1.2 分块触发条件

1. **必须触发新chunk的情况**：
   - 遇到中文一级序号（如"一、"、"二、"等）
   - 遇到Markdown一级标题（`#`）或二级标题（`##`）
   - 当前chunk大小超过阈值且找到合适的分割点

2. **不应触发新chunk的情况**：
   - 遇到中文二级序号（如"（一）"、"（二）"等）
   - 遇到三级及以下序号
   - 注释内容

#### 2.1.3 层级关系保持规则

1. **父子关系保持**：
   - 一级序号与其下属的所有二级序号应保持在同一chunk中
   - 示例：`四、晚期乳腺癌的解救治疗` 与 `（一）激素受体阳性晚期乳腺癌解救治疗`、`（二）HER-2阳性晚期乳腺癌解救治疗` 应在同一chunk

2. **语义完整性**：
   - 标题与其直接内容不应分离
   - 表格与其标题应保持在同一chunk中
   - 列表项与其标题应保持在同一chunk中

### 2.2 数字标题和子标题识别规则

基于对医学诊疗指南文档的深入分析，特别是针对数字标题（如"11维持治疗"、"12姑息治疗"）和子标题（如"(1)"、"(2)"）的分块优化，制定以下详细规则：

#### 2.2.1 数字标题识别与分块

1. **数字标题格式识别**：
   - **纯数字格式**：`^[0-9]+[^0-9].*$`（如"11维持治疗"、"12姑息治疗"）
   - **Markdown格式**：`^#+\s*[0-9]+[^0-9].*$`（如"# 11维持治疗"、"## 12姑息治疗"）
   - **带行号格式**：`^<[0-9]+>[0-9]+[^0-9].*$`（如"<1007>11维持治疗"）

2. **数字标题分块行为**：
   - **最高优先级**：数字标题具有最高的分块优先级（优先级1）
   - **强制分块**：遇到数字标题时必须创建新的chunk边界
   - **向前插入**：chunk边界标记`[CHUNK_BOUNDARY]`插入在数字标题之前

#### 2.2.2 子标题识别与分块策略

1. **子标题格式识别**：
   - **圆括号数字**：`^(\([1-9][0-9]*\))`（如"(1)"、"(2)"、"(10)"）
   - **中文圆括号数字**：`^(（[1-9][0-9]*）)`（如"（1）"、"（2）"、"（10）"）
   - **数字点号**：`^([1-9][0-9]*\.)`（如"1."、"2."、"10."）
   - **数字顿号**：`^([1-9][0-9]*、)`（如"1、"、"2、"、"10、"）

2. **主标题与子标题关联规则**：
   - **第一个子标题保护**：主标题（如"<1007>11维持治疗"）与第一个子标题"(1)"必须保持在同一chunk中
   - **后续子标题分块**：从第二个子标题"(2)"开始，按照指定的token数进行分块
   - **子标题优先级**：子标题具有中等优先级（优先级2），高于普通文本但低于主标题

3. **子标题分块决策逻辑**：
   ```python
   def should_split_at_subtitle(current_chunk_size, subtitle_line, max_chunk_size):
       """决定是否在子标题处分块"""
       # 如果是第一个子标题(1)，不分块
       if re.match(r'^(\([1１]\)|（[1１]）|[1１]\.|[1１]、)', subtitle_line.strip()):
           return False
       
       # 如果当前chunk大小超过阈值，在子标题处分块
       if current_chunk_size > max_chunk_size * 0.8:  # 80%阈值
           return True
           
       return False
   ```

4. **子标题分块边界插入**：
   - **前置插入**：chunk边界标记`[CHUNK_BOUNDARY]`插入在子标题之前，而不是之后
   - **语义保护**：确保子标题与其直接内容不被分离
   - **优先级排序**：子标题 > 段落边界 > 句子边界

#### 2.2.3 数字标题与子标题的层级关系

1. **主从关系识别**：
   ```python
   def detect_title_subtitle_relationship(lines, title_index):
       """检测主标题与子标题的关系"""
       title_line = lines[title_index]
       
       # 检查后续5行内是否有子标题
       for i in range(title_index + 1, min(title_index + 6, len(lines))):
           line = lines[i].strip()
           if not line:
               continue
               
           # 检测子标题格式
           if re.match(r'^(\([1-9]\)|（[1-9]）|[1-9]\.|[1-9]、)', line):
               return True, i  # 返回是否有子标题及其位置
               
       return False, -1
   ```

2. **分块保护策略**：
   - **强制合并**：主标题与第一个子标题"(1)"强制保持在同一chunk中
   - **内容完整性**：子标题与其直接描述内容保持在同一chunk中
   - **表格关联**：如果子标题后跟随表格，优先保持在同一chunk中

3. **典型应用场景**：
   - **治疗方案章节**：如"11维持治疗"包含"(1)维持治疗的目的"、"(2)维持治疗的适应证"等
   - **药物使用指南**：如"用药方案"包含"(1)一线治疗"、"(2)二线治疗"等
   - **诊断标准**：如"诊断流程"包含"(1)初步筛查"、"(2)确诊检查"等

### 2.4 表格分块逻辑详细规则

基于对医学诊疗指南文档中大量表格内容的分析，制定以下表格处理的详细规则：

#### 2.4.1 表格边界检测机制

1. **HTML表格标签识别**：
   - 开始标签：`<table>` 及其变体（如 `<table class="...">`）
   - 结束标签：`</table>`
   - 表格行标签：`<tr>`、`</tr>`
   - 表格单元格标签：`<td>`、`</td>`、`<th>`、`</th>`

2. **表格状态跟踪**：
   - 维护表格开始和结束状态
   - 检测嵌套表格（虽然在医学文档中较少见）
   - 识别表格内的合并单元格（`colspan`、`rowspan`）

3. **表格完整性验证**：
   - 确保每个 `<table>` 都有对应的 `</table>`
   - 验证表格结构的完整性
   - 检测表格内容是否被意外截断

#### 2.4.2 标题-表格关联检测逻辑

1. **前置标题识别**：
   - 检测表格前1-3行内的标题内容
   - 识别描述性文本（如"表1："、"评估标准："等）
   - 匹配中文序号标题与后续表格的关联
   - **特殊识别：冒号结尾标题**：识别以冒号（：）结尾的标题行，这类标题通常引导后续的列表或表格内容

2. **关联强度评估**：
   - **强关联**：标题行后直接跟随表格（中间最多1个空行）
   - **中等关联**：标题行后2-3行内出现表格
   - **弱关联**：标题行后4-5行内出现表格
   - **冒号标题特殊关联**：以冒号结尾的标题与后续5行内的编号列表或表格内容具有强关联性

3. **关联内容保护**：
   - 强关联的标题-表格组合必须保持在同一chunk中
   - 中等关联的组合优先保持在同一chunk中
   - 弱关联的组合在空间允许时保持在同一chunk中
   - **冒号标题保护规则**：以冒号结尾的标题与其后续相关内容（编号列表、表格等）必须保持在同一chunk中

#### 2.4.3 冒号标题与内容关联性规则

1. **冒号标题识别标准**：
   ```python
   def is_title_with_colon(line):
       """识别以冒号结尾的标题行"""
       stripped = line.strip()
       if not stripped:
           return False
       
       # 检查是否以中文冒号或英文冒号结尾
       if stripped.endswith('：') or stripped.endswith(':'):
           # 排除纯数字+冒号的情况（可能是时间）
           if not re.match(r'^\d+[：:]$', stripped):
               return True
       
       return False
   ```

2. **后续内容关联性判断**：
   ```python
   def has_related_content_after_title(lines, title_index, max_look_ahead=5):
       """判断标题后是否有相关的列表或表格内容"""
       for i in range(title_index + 1, min(title_index + max_look_ahead + 1, len(lines))):
           line = lines[i].strip()
           
           # 跳过空行
           if not line:
               continue
               
           # 检查是否为编号列表项
           if re.match(r'^[（(]\d+[）)]', line) or re.match(r'^\d+[.、]', line):
               return True
               
           # 检查是否为其他列表格式
           if line.startswith('- ') or line.startswith('* ') or line.startswith('+ '):
               return True
               
           # 如果遇到其他标题，停止查找
           if get_chunk_boundary_priority(line) > 0:
               break
               
       return False
   ```

3. **分块决策修改**：
   - 当遇到相关内容时，向前查找最多5行寻找冒号标题
   - 如果找到冒号标题，则不进行分块，保持内容与标题在同一chunk中
   - 当遇到冒号标题时，检查后续是否有相关内容，如有则不分块

4. **典型应用场景**：
   - **药物用法列表**：如"乳腺癌内分泌药物用法及用量："后跟编号药物列表
   - **治疗方案表格**：如"治疗方案："后跟方案表格
   - **诊断标准列表**：如"诊断标准："后跟标准列表
   - **评估指标表格**：如"评估指标："后跟指标表格

#### 2.4.4 医学文档表格特殊规则

1. **表格标题识别增强**：
   - **冒号结尾标题**：如"治疗方案："、"用药指南："等
   - **非冒号表格标题**：如"复发或转移性乳腺癌常用的单药化疗方案"、"乳腺癌脑转移局部治疗推荐"等
   - **表格标题模式**：包含"方案"、"推荐"、"治疗"、"药物"、"剂量"等关键词的标题行
   - **表格内容检测**：检测`<table>`标签开始的表格内容

2. **表格标题与内容关联性规则**：
   ```python
   def is_table_title(line):
       """识别表格标题，包括冒号和非冒号格式"""
       stripped = line.strip()
       if not stripped:
           return False
       
       # 冒号结尾的标题
       if stripped.endswith('：') or stripped.endswith(':'):
           return True
           
       # 包含表格相关关键词的标题
       table_keywords = ['方案', '推荐', '治疗', '药物', '剂量', '指征', '标准', '评估', '分级']
       if any(keyword in stripped for keyword in table_keywords):
           return True
           
       return False
   
   def has_table_content_after(lines, title_index, max_look_ahead=10):
       """检查标题后是否有表格内容"""
       for i in range(title_index + 1, min(title_index + max_look_ahead + 1, len(lines))):
           if i >= len(lines):
               break
           line = lines[i].strip()
           if not line:
               continue
           # 检测表格开始标签
           if line.startswith('<table>'):
               return True
           # 检测其他相关内容（列表项等）
           if is_related_to_title(line):
               return True
           # 如果遇到其他标题，停止查找
           if get_chunk_boundary_priority(line) > 0:
               break
       return False
   ```

3. **诊疗评估表格**：
   - **证据特征表格**：包含证据类别、水平、来源、专家共识度的表格
   - **推荐等级表格**：包含推荐等级和标准的表格
   - **病情评估表格**：包含分级标准、评估指标的表格
   - 这些表格具有高优先级，必须保持完整

4. **药物剂量表格**：
   - **血小板生成素剂量表格**：包含用法、推荐剂量、停药指征的表格
   - **化疗方案表格**：包含方案名称、血小板减少症发生率的表格
   - **剂量调整表格**：包含血小板计数和剂量调整方法的表格
   - 这些表格关系到用药安全，必须保持完整

5. **手术指征表格**：
   - **手术适应症表格**：包含手术类型、血小板计数值的表格
   - **MDT构成表格**：包含多学科团队构成和要求的表格
   - 这些表格关系到治疗决策，必须保持完整

6. **特殊格式处理**：
   - **合并单元格**：保持 `colspan` 和 `rowspan` 的完整性
   - **多级表头**：确保表头层次结构的完整性
   - **表格内换行**：处理单元格内的换行符和格式

## 3. 详细处理流程 (Detailed Processing Flow)

脚本的处理流程遵循以下步骤：

### 第一步：读取与分块 (Reading and Chunking)

脚本首先读取整个文档内容，并基于以下逻辑将其拆分为多个初始块（Chunks）：

1.  **基于主标题分块 (Major Heading Chunking)**：
    -   当脚本遇到一级标题 (`#`) 或二级标题 (`##`) 时，会将其视为一个新语义块的开始。
    -   当脚本遇到中文一级序号（如"一、"、"二、"、"三、"等）时，也会将其视为新语义块的开始。
    -   中文子序号（如"（一）"、"（二）"、"（三）"等）不会触发新块的创建，而是与其所属的一级序号保持在同一块中。
    -   当前正在构建的块（如果存在）会在此处结束，并开始一个新的块。这确保了文档的主要章节被清晰地分开。

    **中文序号分块逻辑实现细节**：
    
    - `is_chinese_major_section()` 函数：使用正则表达式 `^[一二三四五六七八九十]+、[^（）]*$` 识别中文一级序号
    - `is_chinese_sub_section()` 函数：使用正则表达式 `^（[一二三四五六七八九十]+）` 识别中文二级序号
    - `should_start_new_chunk()` 函数：决定是否创建新chunk的核心逻辑
      - 当遇到标题级别为1或2的Markdown标题时触发新chunk
      - 当遇到中文一级序号时触发新chunk
      - **重要修复**：当遇到中文二级序号时不应触发新chunk，需要检查其父级一级序号的存在

2.  **处理过长的块 (Handling Large Chunks)**：
    -   为了避免单个块超出 LLM 的处理能力，脚本设定了块的最大行数阈值。
    -   如果一个块的行数超过了该阈值，脚本会从后向前寻找一个合适的分割点。
    -   合适的分割点优先选择次级标题（`###` 或更低级别）或空行。这样可以在保持局部上下文完整性的前提下，对大块进行拆分。

### 第二步：合并注释块 (Merging Comment Chunks)

在初始分块完成后，脚本会进行一次后处理，以确保注释的连续性：

-   脚本会遍历所有块。
-   如果一个块的开头内容是“注释”，它将被自动与前一个块合并。
-   这个步骤确保了注释不会与其描述的正文内容分离。

### 第三步：表格边界检测与保护 (Table Boundary Detection and Protection)

在分块操作中，脚本会特别处理表格内容以确保其完整性：

1.  **表格边界检测**：
    -   使用 `detect_table_boundaries()` 函数扫描文档中的所有HTML表格标签
    -   识别 `<table>` 和 `</table>` 标签对，建立表格边界映射
    -   检测表格内的行标签 `<tr>` 和单元格标签 `<td>`、`<th>`
    -   处理表格内的合并单元格（`colspan`、`rowspan`）

2.  **标题-表格关联检测**：
    -   使用 `check_title_table_association()` 函数检测表格前的相关标题
    -   识别描述性文本（如"表1："、"评估标准："等）
    -   评估标题与表格的关联强度（强关联、中等关联、弱关联）
    -   确保关联的标题-表格组合保持在同一chunk中

3.  **医学关键表格识别**：
    -   使用 `is_medical_critical_table()` 函数识别医学文档中的关键表格
    -   特别保护诊疗评估表格、药物剂量表格、手术指征表格等
    -   为关键表格提供最高优先级的完整性保护

### 第四步：主标题和子标题关系检测与保护 (Main Title and Subtitle Relationship Detection and Protection)

在分块操作中，脚本会特别检测和保护主标题与其紧邻子标题的关系：

1.  **主标题和子标题关系检测**：
    -   使用 `has_immediate_sub_heading()` 函数检测主标题后是否紧跟子标题
    -   检测范围：主标题后的5行内容
    -   识别模式：
        - Markdown子标题（`##`、`###`、`####`等）
        - 中文二级序号（如"（一）"、"（二）"等）
        - 数字序号（如"1."、"2."等）
        - 字母序号（如"a)"、"b)"等）

2.  **关系保护逻辑**：
    -   当检测到主标题后紧跟子标题时，不在它们之间插入边界标记
    -   确保主标题和其紧邻的子标题保持在同一chunk中
    -   维护文档的层次结构完整性

3.  **检测算法实现**：
    ```python
    def has_immediate_sub_heading(lines, current_index):
        """
        检测主标题后是否紧跟子标题
        
        Args:
            lines: 文档行列表
            current_index: 当前主标题的行索引
            
        Returns:
            bool: 如果紧跟子标题返回True，否则返回False
        """
        # 检查后续5行内容
        for i in range(current_index + 1, min(current_index + 6, len(lines))):
            line = lines[i].strip()
            if not line:  # 跳过空行
                continue
                
            # 检测各种子标题模式
            if (line.startswith('##') or  # Markdown子标题
                re.match(r'^（[一二三四五六七八九十]+）', line) or  # 中文二级序号
                re.match(r'^\d+\.', line) or  # 数字序号
                re.match(r'^[a-zA-Z]\)', line)):  # 字母序号
                return True
                
            # 如果遇到其他内容，停止检测
            if line and not line.startswith('#'):
                break
                
        return False
    ```

4.  **边界标记优化**：
    -   在 `create_chunks()` 函数中集成关系检测逻辑
    -   修改分块条件：当主标题后紧跟子标题时，延迟创建新chunk
    -   确保相关内容的语义完整性

### 第五步：格式化并写入文件 (Formatting and Writing)

在分块和合并操作完成后，脚本会生成最终的优化文件：

1.  **添加文档边界**：
    -   在文件的最开始写入 `====== 文档开始 ======`。
    -   在文件的最末尾写入 `====== 文档结束 ======`。

2.  **遍历块并添加内容**：
    -   脚本逐一处理每个最终确定的块。
    -   在每个块内部，为每一行非空文本添加行号标记，格式为 `<行号>`。例如：`<1>这是第一行内容`。
    -   空行被保留，以维持原始的段落间距。

3.  **插入块边界标记**：
    -   在每个块（除了最后一个）的末尾，插入一个清晰的块边界标记 `[CHUNK_BOUNDARY]`。

### 第六步：质量检测和输出 (Quality Detection and Output)

每次文档转换完成后，脚本会自动进行质量检测和详细输出：

1.  **边界标记质量检测**：
    -   统计总边界标记数量
    -   检测主标题与紧邻子标题被错误分开的情况
    -   计算边界标记的准确率和质量分数

2.  **主标题和子标题关系验证**：
    ```python
    def verify_title_subtitle_relationships(file_path):
        """
        验证主标题和子标题关系的完整性
        
        Args:
            file_path: 处理后的文档路径
            
        Returns:
            dict: 包含验证结果的详细报告
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        main_titles = []
        boundary_issues = []
        
        # 查找所有主标题
        for i, line in enumerate(lines):
            line = line.strip()
            if (line.startswith('#') and not line.startswith('##')) or \
               re.match(r'^[一二三四五六七八九十]+、', line):
                main_titles.append((i, line))
        
        # 检查每个主标题与紧邻子标题的关系
        for title_idx, title_content in main_titles:
            # 检查后续5行
            for j in range(title_idx + 1, min(title_idx + 6, len(lines))):
                next_line = lines[j].strip()
                
                # 如果遇到边界标记
                if '[CHUNK_BOUNDARY]' in next_line:
                    # 检查边界标记后是否紧跟子标题
                    if j + 1 < len(lines):
                        after_boundary = lines[j + 1].strip()
                        if is_subtitle(after_boundary):
                            boundary_issues.append({
                                'main_title_line': title_idx + 1,
                                'main_title': title_content,
                                'boundary_line': j + 1,
                                'subtitle_line': j + 2,
                                'subtitle': after_boundary
                            })
                    break
                    
                # 如果遇到子标题但没有边界标记，这是正确的
                if is_subtitle(next_line):
                    break
        
        return {
            'total_main_titles': len(main_titles),
            'boundary_issues': boundary_issues,
            'issues_count': len(boundary_issues),
            'success_rate': (len(main_titles) - len(boundary_issues)) / len(main_titles) * 100 if main_titles else 100
        }
    ```

3.  **详细输出报告**：
    -   文档总行数和边界标记总数
    -   主标题数量和分布情况
    -   检测到的问题案例详细信息
    -   整体处理成功率和质量评估
    -   优化建议和改进方向

4.  **自动化检测触发**：
    -   每次调用 `preprocess_file()` 函数后自动触发检测
    -   在控制台输出详细的检测结果
    -   生成检测日志文件供后续分析
    -   该标记前后会留有空行，以增强可读性。

4.  **保存文件**：
    -   最终生成的内容被写入一个新的文件中。
    -   新文件的命名规则是在原文件名后添加 `_optimized` 后缀（例如 `original.md` -> `original_optimized.md`），并保存在同一目录下。

## 4. 脚本用法 (Script Usage)

可以通过以下命令行指令来运行此预处理脚本：

```bash
python3 preprocess.py "/path/to/your/document.md"
```

-   请确保将 `/path/to/your/document.md` 替换为需要处理的文件的**绝对路径**。

## 5. 示例 (Example)

**原始 Markdown 内容:**

```markdown
# 第一章：简介

这是第一章的介绍内容。

## 1.1 背景

这里是关于背景的详细说明。

注释：这是一个重要的背景注释。

# 第二章：方法

这是第二章的介绍。
```

**处理后的 `_optimized.md` 内容:**

```markdown
====== 文档开始 ======

<1># 第一章：简介
<2>
<3>这是第一章的介绍内容。
<4>
<5>## 1.1 背景
<6>
<7>这里是关于背景的详细说明。
<8>
<9>注释：这是一个重要的背景注释。

[CHUNK_BOUNDARY]

<10># 第二章：方法
<11>
<12>这是第二章的介绍。

====== 文档结束 ======
```

## 6. 问题分析与修复方案 (Problem Analysis and Fix Solutions)

### 6.1 发现的问题

在对 `乳腺癌诊疗指南2025_optimized_v2.md` 的分块结果分析中，发现了以下关键问题：

#### 6.1.1 中文序号分块问题

1. **中文序号层级关系被破坏**：
   - 问题位置：第279-282行
   - 具体表现：`四、晚期乳腺癌的解救治疗` 与其子章节 `（一）激素受体阳性晚期乳腺癌解救治疗`、`（二）HER-2阳性晚期乳腺癌解救治疗` 被强制分离到不同的chunk中

2. **分块边界位置错误**：
   - 问题位置：第2215-2221行
   - 具体表现：`[CHUNK_BOUNDARY]` 被错误地放置在 `<1696># 4.特殊时期的患者管理` 之前，而不是在 `<1700>十二、循环肿瘤标志物检测和临床应用` 之前
   - 根本原因：中文一级序号"十二、"应该触发新chunk创建，但分块逻辑未正确识别其优先级

3. **分块逻辑缺陷**：
   - `should_start_new_chunk()` 函数只检查标题级别，未考虑中文序号的层级关系
   - 导致所有标题级别为1或2的行都触发新chunk创建，包括应该保持在一起的子序号
   - 中文序号的优先级判断逻辑存在缺陷，导致边界位置计算错误

#### 6.1.2 表格分块问题

1. **表格内容截断**：
   - 问题表现：表格在分块时被截断，导致表格结构不完整
   - 影响：医学诊疗指南中的关键信息（如药物剂量、评估标准）丢失

2. **标题-表格分离**：
   - 问题表现：表格标题与表格内容被分割到不同的chunk中
   - 影响：表格失去上下文，无法理解表格的具体含义和用途

3. **医学关键信息丢失**：
   - 问题表现：诊疗评估表格、药物剂量表格等关键信息被不当分割
   - 影响：可能导致医疗决策信息不完整，存在安全风险

### 6.2 根本原因分析

**当前 `should_start_new_chunk()` 函数的问题逻辑**：
```python
def should_start_new_chunk(line, current_chunk_size, max_chunk_size):
    heading_level = get_heading_level(line)
    if heading_level in [1, 2] or is_chinese_major_section(line):
        return True
    # ... 其他逻辑
```

**问题所在**：
- 函数将所有标题级别为1或2的行都视为新chunk的开始
- 中文二级序号（如"（一）"、"（二）"）也被 `get_heading_level()` 识别为级别2
- 缺少对中文序号层级关系的上下文检查
- **优先级判断错误**：在第2215-2221行的案例中，`# 4.特殊时期的患者管理` 被错误地优先于 `十二、循环肿瘤标志物检测和临床应用` 进行分块

**具体案例分析**：
```
<1696># 4.特殊时期的患者管理          ← 错误：这里被放置了[CHUNK_BOUNDARY]
<1698>在重大突发公共卫生事件期间...
<1700>十二、循环肿瘤标志物检测和临床应用  ← 正确：应该在这里放置[CHUNK_BOUNDARY]
```

**错误原因**：
1. 分块逻辑优先处理了Markdown标题 `# 4.特殊时期的患者管理`
2. 未正确识别中文一级序号 `十二、` 的更高优先级
3. 缺少对混合标题格式（Markdown + 中文序号）的正确处理逻辑

### 6.3 修复方案

#### 6.3.1 修复 `should_start_new_chunk()` 函数

**修复后的逻辑**：
```python
def should_start_new_chunk(line, current_chunk_size, max_chunk_size, 
                          context_lines=None, in_table=False, table_start_line=None):
    """
    决定是否应该开始一个新的chunk
    
    参数:
    - line: 当前行内容
    - current_chunk_size: 当前chunk大小
    - max_chunk_size: 最大chunk大小
    - context_lines: 上下文行，用于检查层级关系
    - in_table: 是否在表格内部
    - table_start_line: 表格开始行号
    
    返回:
    - bool: 是否应该开始新chunk
    """
    # 表格保护：如果在表格内部，不允许分块
    if in_table:
        return False
    
    # 检查是否为表格开始，需要检查标题-表格关联
    if '<table' in line.lower():
        # 检查是否有关联的标题需要保护
        title_association = check_title_table_association(line, context_lines)
        if title_association['should_protect']:
            return False
    
    # **关键修复**：优先级判断逻辑
    # 1. 最高优先级：中文一级序号（如"十二、"）
    if is_chinese_major_section(line):
        return True
    
    # 2. 中等优先级：中文二级序号（不应该触发新chunk）
    if is_chinese_sub_section(line):
        return False
    
    # 3. 较低优先级：Markdown标题
    heading_level = get_heading_level(line)
    if heading_level in [1, 2]:
        # 检查是否存在更高优先级的中文序号在附近
        if context_lines:
            for i, context_line in enumerate(context_lines[-5:]):  # 检查前5行
                if is_chinese_major_section(context_line):
                    # 如果附近有中文一级序号，降低Markdown标题的优先级
                    return False
        return True
    
    # 基于大小的分块逻辑
    if current_chunk_size > max_chunk_size * 0.3:
        return True
    
    return False

def get_chunk_boundary_priority(line):
    """
    获取分块边界的优先级
    
    返回:
    - int: 优先级数值，数值越高优先级越高
    """
    if is_chinese_major_section(line):
        return 100  # 最高优先级
    elif is_chinese_sub_section(line):
        return 0    # 不触发分块
    elif get_heading_level(line) == 1:
        return 80   # 高优先级
    elif get_heading_level(line) == 2:
        return 70   # 中高优先级
    else:
        return 10   # 低优先级
```

#### 6.3.2 增强层级关系检查

**新增函数**：
```python
def check_chinese_hierarchy_context(current_line, previous_lines, max_lookback=10):
    """
    检查中文序号的层级关系上下文
    
    参数:
    - current_line: 当前行
    - previous_lines: 前面的行列表
    - max_lookback: 最大回溯行数
    
    返回:
    - dict: 包含层级关系信息的字典
    """
    if not is_chinese_sub_section(current_line):
        return {"is_sub_section": False}
    
    # 在前面的行中查找对应的一级序号
    for i in range(min(len(previous_lines), max_lookback)):
        prev_line = previous_lines[-(i+1)]
        if is_chinese_major_section(prev_line):
            return {
                "is_sub_section": True,
                "parent_found": True,
                "parent_line": prev_line,
                "distance": i+1
            }
    
    return {
        "is_sub_section": True,
        "parent_found": False,
        "distance": -1
    }

def check_title_table_association(table_line, context_lines, max_lookback=5):
    """
    检查表格与前置标题的关联性
    
    参数:
    - table_line: 表格开始行
    - context_lines: 上下文行列表
    - max_lookback: 最大回溯行数
    
    返回:
    - dict: 包含关联信息的字典
    """
    if not context_lines:
        return {"should_protect": False, "association_strength": "none"}
    
    # 检查前面几行是否有标题或描述性文本
    for i in range(min(len(context_lines), max_lookback)):
        prev_line = context_lines[-(i+1)].strip()
        if not prev_line:  # 跳过空行
            continue
            
        # 检查是否为标题行
        if (is_chinese_major_section(prev_line) or 
            is_chinese_sub_section(prev_line) or 
            get_heading_level(prev_line) > 0 or
            "表" in prev_line or "评估" in prev_line or "标准" in prev_line):
            
            # 根据距离判断关联强度
            if i <= 1:  # 强关联
                return {"should_protect": True, "association_strength": "strong"}
            elif i <= 3:  # 中等关联
                return {"should_protect": True, "association_strength": "medium"}
            else:  # 弱关联
                return {"should_protect": False, "association_strength": "weak"}
    
    return {"should_protect": False, "association_strength": "none"}

def detect_table_boundaries(lines):
    """
    检测文档中所有表格的边界
    
    参数:
    - lines: 文档行列表
    
    返回:
    - list: 表格边界信息列表
    """
    table_boundaries = []
    in_table = False
    table_start = None
    
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        
        if '<table' in line_lower and not in_table:
            in_table = True
            table_start = i
        elif '</table>' in line_lower and in_table:
            in_table = False
            table_boundaries.append({
                'start': table_start,
                'end': i,
                'type': 'html_table'
            })
            table_start = None
    
    return table_boundaries

def is_medical_critical_table(table_content):
    """
    判断是否为医学关键表格
    
    参数:
    - table_content: 表格内容
    
    返回:
    - bool: 是否为关键表格
    """
    critical_keywords = [
        "证据", "推荐等级", "血小板", "剂量", "用法", 
        "适应症", "禁忌症", "评估", "诊断", "治疗方案",
        "MDT", "多学科", "手术指征", "化疗方案"
    ]
    
    table_text = ' '.join(table_content) if isinstance(table_content, list) else str(table_content)
    
    return any(keyword in table_text for keyword in critical_keywords)
```

### 6.4 验证和测试

#### 6.4.1 测试用例

**测试文档结构**：
```markdown
四、晚期乳腺癌的解救治疗

（一）激素受体阳性晚期乳腺癌解救治疗
内容1...

（二）HER-2阳性晚期乳腺癌解救治疗  
内容2...

五、预后评估

（一）生存率分析
内容3...
```

**期望的分块结果**：
- Chunk 1: 包含"四、晚期乳腺癌的解救治疗"及其所有子章节"（一）"、"（二）"
- Chunk 2: 包含"五、预后评估"及其子章节"（一）"

#### 6.4.2 中文序号层级测试
1. **中文序号层级测试**：
   - 测试包含多级中文序号的文档
   - 验证子序号与父序号保持在同一chunk中
   - 检查层级关系的正确性

#### 6.4.3 表格处理测试
1. **表格边界检测测试**：
   - 测试包含HTML表格的医学文档
   - 验证表格开始和结束标签的正确识别
   - 检查嵌套表格和复杂表格结构的处理

2. **标题-表格关联测试**：
   - 测试表格前有标题的情况
   - 验证不同距离的标题-表格关联强度评估
   - 检查关联内容是否保持在同一chunk中

3. **医学关键表格测试**：
   - 测试诊疗评估表格的完整性保护
   - 验证药物剂量表格的正确处理
   - 检查手术指征表格的保护机制

### 6.5 边界位置修正实现方案

#### 6.5.1 多遍扫描算法

为了解决边界位置错误的问题，建议采用多遍扫描算法：

```python
def optimize_chunk_boundaries(chunks, original_lines):
    """
    优化chunk边界位置，确保高优先级的分块点被正确识别
    
    参数:
    - chunks: 初始分块结果
    - original_lines: 原始文档行列表
    
    返回:
    - list: 优化后的chunk列表
    """
    # 第一遍：识别所有潜在的分块点及其优先级
    potential_boundaries = []
    for i, line in enumerate(original_lines):
        priority = get_chunk_boundary_priority(line)
        if priority > 0:
            potential_boundaries.append({
                'line_index': i,
                'priority': priority,
                'content': line.strip()
            })
    
    # 第二遍：根据优先级重新调整边界
    optimized_chunks = []
    current_chunk = []
    last_boundary_index = 0
    
    # 按优先级排序边界点
    potential_boundaries.sort(key=lambda x: (-x['priority'], x['line_index']))
    
    for boundary in potential_boundaries:
        line_index = boundary['line_index']
        
        # 检查是否应该在此处创建边界
        if should_create_boundary_here(line_index, last_boundary_index, original_lines):
            # 创建当前chunk
            if current_chunk:
                optimized_chunks.append(current_chunk)
            
            # 开始新chunk
            current_chunk = original_lines[last_boundary_index:line_index]
            last_boundary_index = line_index
    
    # 添加最后一个chunk
    if current_chunk or last_boundary_index < len(original_lines):
        final_chunk = original_lines[last_boundary_index:]
        if final_chunk:
            optimized_chunks.append(final_chunk)
    
    return optimized_chunks

def should_create_boundary_here(line_index, last_boundary_index, original_lines):
    """
    判断是否应该在指定位置创建边界
    
    参数:
    - line_index: 当前行索引
    - last_boundary_index: 上一个边界索引
    - original_lines: 原始文档行列表
    
    返回:
    - bool: 是否应该创建边界
    """
    # 避免创建过小的chunk
    min_chunk_size = 100  # 最小字符数
    current_chunk_content = ''.join(original_lines[last_boundary_index:line_index])
    
    if len(current_chunk_content.strip()) < min_chunk_size:
        return False
    
    # 检查是否在表格内部
    if is_inside_table(line_index, original_lines):
        return False
    
    return True

def fix_boundary_position_error():
    """
    修复类似第2215-2221行的边界位置错误
    
    具体修复逻辑：
    1. 识别错误放置的边界（如在Markdown标题前）
    2. 查找附近的高优先级分块点（如中文一级序号）
    3. 重新调整边界位置
    """
    # 实现具体的修复逻辑
    pass
```

#### 6.5.2 边界验证机制

```python
def validate_chunk_boundaries(chunks):
    """
    验证chunk边界的正确性
    
    参数:
    - chunks: chunk列表
    
    返回:
    - dict: 验证结果
    """
    validation_results = {
        'errors': [],
        'warnings': [],
        'suggestions': []
    }
    
    for i, chunk in enumerate(chunks):
        # 检查是否存在中文序号层级关系被破坏的情况
        chinese_sections = find_chinese_sections_in_chunk(chunk)
        if has_broken_hierarchy(chinese_sections):
            validation_results['errors'].append({
                'chunk_index': i,
                'type': 'broken_chinese_hierarchy',
                'description': '中文序号层级关系被破坏'
            })
        
        # 检查是否存在表格被截断的情况
        if has_truncated_table(chunk):
            validation_results['errors'].append({
                'chunk_index': i,
                'type': 'truncated_table',
                'description': '表格内容被截断'
            })
    
    return validation_results
```

#### 6.4.4 边界情况测试
1. **边界情况测试**：
   - 测试chunk大小接近阈值时的行为
   - 验证在不同文档结构下的表现
   - 检查异常输入的处理

2. **性能测试**：
   - 测试大文档的处理性能
   - 验证内存使用情况
   - 检查处理时间的合理性

#### 6.4.5 集成测试
1. **完整文档测试**：
   - 使用真实的医学诊疗指南文档进行测试
   - 验证表格和中文序号同时存在时的处理
   - 检查整体分块质量和语义完整性

#### 6.4.6 修复效果验证

修复后的分块逻辑应该能够：
1. 正确识别中文一级序号和二级序号的层级关系
2. 保持父子章节在同一chunk中
3. 避免不必要的chunk分割
4. 维护文档的语义完整性
5. 保护表格内容的完整性
6. 维护标题-表格的关联关系

### 6.5 实施建议

#### 6.5.1 分阶段实施策略

1. **第一阶段：中文序号处理修复**：
   - 修复`should_start_new_chunk`函数的中文序号处理逻辑
   - 添加`check_chinese_hierarchy_context`函数
   - 进行中文序号相关的测试验证

2. **第二阶段：表格处理功能添加**：
   - 实现`detect_table_boundaries`函数
   - 添加`check_title_table_association`函数
   - 实现`is_medical_critical_table`函数
   - 修改主分块逻辑以支持表格保护

3. **第三阶段：集成测试和优化**：
   - 进行完整的医学文档测试
   - 性能优化和内存使用优化
   - 建立监控和反馈机制

#### 6.5.2 技术实施要点

1. **代码结构优化**：
   - 保持函数的单一职责原则
   - 添加详细的函数注释和类型提示
   - 确保代码的可维护性和可扩展性

2. **配置管理**：
   - 将表格检测的关键词配置化
   - 支持不同类型医学文档的特殊规则配置
   - 提供灵活的参数调整机制

3. **错误处理**：
   - 添加表格标签不匹配的异常处理
   - 处理格式不规范的HTML表格
   - 提供降级处理机制

#### 6.5.3 质量保证措施

1. **备份策略**：
   - 在修改前备份原始的`preprocess_optimized.py`文件
   - 保留原始分块结果作为对比基准
   - 建立版本控制和回滚机制

2. **监控指标**：
   - 分块数量的变化
   - 平均chunk大小的变化
   - 语义完整性的提升程度
   - 表格完整性保护率
   - 标题-表格关联保护率

3. **测试覆盖**：
   - 单元测试覆盖所有新增函数
   - 集成测试覆盖完整的分块流程
   - 回归测试确保原有功能不受影响

#### 6.5.4 部署和维护

1. **渐进式部署**：
   - 先在测试环境验证新逻辑
   - 小批量文档试运行
   - 逐步扩大到全量文档处理

2. **持续监控**：
   - 建立分块质量监控仪表板
   - 设置异常情况告警机制
   - 定期评估和优化分块效果

3. **反馈机制**：
   - 建立用户反馈收集渠道
   - 快速响应和修复问题
   - 持续改进分块算法

通过以上修复方案，可以有效解决中文序号分块逻辑错误和表格处理不当的问题，确保RAG系统能够获得更高质量的文档chunk。主要改进包括：

1. **中文序号层级关系修复**：确保子序号与父序号保持在同一chunk中，维护文档的逻辑结构
2. **表格完整性保护**：防止表格在分块时被截断，保持医学关键信息的完整性
3. **标题-表格关联维护**：确保表格标题与表格内容保持在同一chunk中，提供完整的上下文
4. **医学文档特殊处理**：针对诊疗指南中的评估体系、药物剂量等关键表格提供特殊保护

这些改进将显著提升RAG系统在医学文档处理方面的准确性和可靠性，为医疗决策提供更好的信息支持。