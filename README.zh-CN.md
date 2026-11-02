# Piano Score Refiner

[English](README.md) | [简体中文](README.zh-CN.md)

用于整理钢琴自动扒谱初稿的 AI Agent Skill。接收已有的 MIDI、MusicXML 或 MuseScore 工程文件，指导 AI 助手调整左右手分配、清理多声部冗余休止符、优化谱号与版面，并在修改后核对音符力度与踏板等播放数据。

## 背景

使用自动扒谱工具（如 Transkun 等音频转 MIDI 模型）生成的钢琴谱初稿，虽然音高和时值大多准确，但直接导入打谱软件后往往难以直接视奏：

- 左右手常按固定音高机械切分，伴奏与旋律分配别扭；
- 多声部重叠容易拆出大量辅助休止符，谱面显得杂乱；
- 高低音区加线过多，或局部换谱号、八度线标记不清晰；
- 延音线和符杠分组不符合拍号习惯，节拍难数；
- 手动或用脚本重排声部后，容易丢失原有的逐音力度（Velocity）和踏板控制事件（CC64/CC67）。

本项目将这些修谱规则与检查步骤整理为结构化的 Agent Skill，供 Codex 等具备文件处理能力的 AI 助手按流程修正谱面并验证回放数据。

## 主要功能

| 常见问题 | 处理方式 |
|---|---|
| 按固定音高机械分手，弹奏不顺手 | 结合前后手位移动、当前持音和另一只手的负担重新分配左右手 |
| 多声部休止符密集，同拍音符符干分散 | 合并时值相容的和弦；仅隐藏被同谱表其他声部完整覆盖的冗余休止符，保留不同时值的独立声部 |
| 节拍难认，延音线与符杠拆分混乱 | 按拍号重新梳理符杠分组、跨拍休止与延音线，保证各声部小节时值完整 |
| 加线过多，局部谱号或八度容易看错 | 调整局部谱号或 8va 标记，按需在加线较多或大跳位置添加稀疏音名提示 |
| 修谱后回放变死板或踏板丢失 | 比对修改前后的音符起止、逐音力度、速度与踏板事件，确保播放属性不丢失 |
| 编辑界面与导出 PDF 显示不一致 | 分别检查打谱软件的隐藏元素视图与 PDF 渲染结果 |

默认仅优化记谱与显示，保持原有的音高、时值和演奏数据不变。如需删减音符、移调、截短长音或改写滚奏，可在提示词中单独说明。

## 使用方法

将本目录下的 `README.md`、`SKILL.md` 和 `SOP.md` 放在同一文件夹中（或安装到 AI 助手的 `skills` 目录），连同待整理的乐谱文件一起交给支持文件操作的 AI 助手。

可以使用以下提示词：

```text
请读取 piano-score-refiner/SKILL.md，并按 SOP.md 的规则整理这份钢琴谱。

目标是让谱面更清晰、方便双手视奏。请先解析乐谱的结构化数据，依次检查左右手分配、持音跨度、多声部与休止符、节拍写法、谱号与页面排版。
默认保持原有音高、音长、逐音力度和踏板数据不变。如果输入是未量化的原始演奏 MIDI，请保留原 MIDI 文件并说明量化带来的时序变化。
完成后请导出可编辑工程文件、PDF，并附上修改摘要与校验结果。如有必须通过改编（如删音或移八度）才能解决的跨度难点，请先列出来。
```

如果有特定需求（例如只修第一页、在加线音符旁标注音名、或按特定手幅调整），直接在提示词中补充即可。

### 输入与输出

- **推荐输入**：优先提供 `.mscz / .mscx`（MuseScore 工程）或 `.musicxml / .mxl`，这类文件已包含谱表与声部结构。如果只有 `.mid / .midi` 也可以处理，首次制谱时需先确定拍号与量化方式。若只有扫描版 PDF 或图片，需先通过 OMR 工具转为结构化乐谱。
- **可选参考**：原音频、原始演奏 MIDI 或标出问题小节的截图。
- **交付内容**：整理后的可编辑工程（`.mscz`）、打印版 `.pdf`（以及按需导出的 `.mid`），附带修改小节说明、保留的大跨度难点位置及播放数据核对结果。

## 参考工作流：从音频到乐谱

本 Skill 不绑定特定的转录模型。如果手头已有 MIDI 或打谱工程，可以直接跳到上面的谱面整理步骤；如果从音频或视频开始，可以参考以下开源工具链：

`音频提取 (FFmpeg) → 钢琴转录 (Transkun) → 初稿生成 (pretty_midi / music21) → 谱面整理与排版 (Piano Score Refiner + MuseScore Studio)`

| 工具 / 库 | 用途 | 链接 |
|---|---|---|
| FFmpeg | 从视频或音频源提取标准音频 | [官网下载](https://ffmpeg.org/download.html) |
| Transkun | 将钢琴音频转录为包含力度与踏板的 MIDI | [GitHub](https://github.com/Yujia-Yan/Transkun) |
| pretty_midi | 读取与处理 MIDI 音符及控制事件 | [GitHub](https://github.com/craffel/pretty-midi) |
| music21 | 处理节奏、声部并生成 MusicXML 初稿 | [官方文档](https://www.music21.org/music21docs/) |
| MuseScore Studio | 乐谱编辑、声部与排版微调、回放及导出 PDF | [官网下载](https://musescore.org/en/download) |

### 环境要求

- **Python 3.12**（已测试），Windows 或 Linux，建议使用虚拟环境。
- **FFmpeg** 必须在 `PATH` 中（可用 `ffmpeg -version` 检查），否则 `run.py` 会报 `FFmpeg is not on PATH`。输入已是 MIDI 时不需要。
- **GPU**：`run.py` 默认 `--device cuda`（在 NVIDIA 显卡 + CUDA 12.4 下测试）。没有 CUDA 显卡时请加 `--device cpu`。
- **模型权重**：Transkun 安装包自带权重（`transkun/pretrained/2.0.pt`），无需另外下载。
- **MuseScore Studio 4.x**（可选）：仅在传入 `--musescore` 时用于导出 PDF；否则使用 Verovio + resvg + PyMuPDF 渲染。
- **音色库**（可选，仅影响回放）：[Salamander Grand Piano](https://freepats.zenvoid.org/Piano/acoustic-grand-piano.html)（如 SalC5Light2 `.sf2` 版本）与 [GeneralUser GS](https://schristiancollins.com/generaluser.php)。将 `.sf2` 放入 `文档/MuseScore4/SoundFonts`，参见 [MuseScore 手册](https://musescore.org/en/handbook/4/soundfonts-and-sfz-files)。

### 安装

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows PowerShell；Linux/macOS：source .venv/bin/activate
# 先从 PyTorch 官方索引安装（仅 CPU 时改用 .../whl/cpu）
pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
```

Windows 上 Transkun 依赖链中的 `ncls` 可能需要编译；若 `pip` 安装失败，请先安装 Microsoft C++ Build Tools。

### 运行

1. 运行 [`scripts/run.py`](scripts/run.py) 将钢琴音频/视频或 MIDI 转为原始演奏 MIDI（`performance.mid`）、量化 MIDI（`score-quantized.mid`）、初稿 `score.musicxml`、预览 PDF 及 `run.json`，并可用 [`scripts/verify_score.py`](scripts/verify_score.py) 核对 MusicXML 音符与延音线完整性：
   ```bash
   python scripts/run.py input_audio.mp3 --out ./draft_out --device cuda
   python scripts/run.py input_audio.mp3 --out ./draft_cpu --device cpu --musescore "C:\Program Files\MuseScore 4\bin\MuseScore4.exe"
   python scripts/verify_score.py ./draft_out
   ```
   `--out` 必须是尚不存在的新目录，不会覆盖已有结果。
2. 将生成的初稿交给 AI 助手结合本 Skill 与 MuseScore 进行谱面精修。

`run.py` 常用参数：

| 参数 | 用法 |
|---|---|
| `--device cuda\|cpu` | 推理设备，默认 `cuda` |
| `--musescore <exe>` | 用 MuseScore 导出 PDF，替代默认的 Verovio 渲染 |
| `--bpm 80 --meter 3/4` | 人工指定速度与拍号；默认 `4/4` 是假设，不是检测结果 |
| `--grid 4` | 每四分音符等分数（2、3、4、6、8），4 即十六分音符网格 |
| `--split 60` | 初始分手的 MIDI 音高阈值，低于它归左手 |
| `--key G` | 调号，如 `G` 为 G 大调，`e` 为 e 小调 |
| `--title` | 谱面标题 |
| `--segment 16` | 转录分窗秒数（步长为一半），显存紧张时可减小 |
| `--midi-only` | 只转录 MIDI，跳过制谱 |
| `--timing-map <json>` | 明确的时间映射，如 `{"seconds":[0,1,2],"quarters":[0,2,4]}` |
| `--hand-map <json>` | 分段分手音高与左手谱号，如 `[{"seconds":0,"split":73,"left_clef":"treble"}]` |

已有 `performance.mid` 时可直接作为输入，只重做制谱而不重新运行模型。

> **环境参考**：本工作流在 Python 3.12、PyTorch/torchaudio 2.6.0 (CUDA 12.4)、Transkun 2.0.1、music21 10.5.0 及 MuseScore Studio 4.7.5 环境下测试通过。回放音色曾配合 Salamander C5 Light 与 GeneralUser GS 使用（音色库仅影响回放听感，不影响音符识别与修谱）。

## 文件结构

| 文件 | 说明 |
|---|---|
| [README.md](README.md) | English project overview and usage guide |
| [README.zh-CN.md](README.zh-CN.md) | 中文版项目背景、功能概览、使用方法与参考工具链 |
| [SKILL.md](SKILL.md) | 英文 AI Agent 入口，定义适用场景、处理模式与核心流程 |
| [SKILL.zh-CN.md](SKILL.zh-CN.md) | 中文版 AI Agent 执行说明 |
| [SOP.md](SOP.md) | 英文修谱规范，涵盖输入解析、节拍与声部、双手分配、版面标注及验收标准 |
| [SOP.zh-CN.md](SOP.zh-CN.md) | 中文版修谱规则与验收标准 |
| [requirements.txt](requirements.txt) | 辅助脚本的 Python 依赖（PyTorch 需单独安装） |
| [scripts/run.py](scripts/run.py) | 从音频/视频或原始 MIDI 生成初稿 MusicXML、量化 MIDI 与预览 PDF 的辅助脚本 |
| [scripts/verify_score.py](scripts/verify_score.py) | 核对 MusicXML 音符、起止时值与跨小节延音线是否与量化 MIDI 一致的校验脚本 |
| [LICENSE](LICENSE) | MIT 开源许可证 |

## 反馈与贡献

欢迎通过 Issue 或 Pull Request 提交反馈。反映具体修谱问题时，建议附上对应小节的修改前后截图、最小复现文件（MIDI / MusicXML / MSCZ）以及期望的记谱写法，并注明问题属于认音、节拍、分手、排版还是回放数据丢失，以便进一步完善规则。

## 致谢与许可

部分工具链组合思路参考了 [piano-2-sheet](https://github.com/thanhpt1110/piano-2-sheet)。`run.py` 默认使用 Verovio、resvg_py 与 PyMuPDF 渲染初稿 PDF；传入 `--musescore` 时改用 MuseScore Studio 导出。

本项目采用 [MIT License](LICENSE) 开源，相关上游工具与模型遵循各自原有的开源许可证；其中 PyMuPDF 为 AGPL-3.0／商业双许可，Verovio 为 LGPL-3.0，整套工具链不能统称 MIT。
