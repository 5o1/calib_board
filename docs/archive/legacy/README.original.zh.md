# 采集台统一标定板 station_calib_board — v1.1 推荐打印版

独立的 A3 定尺打印标定板：OpenCV ChArUco 几何标定、8 级名义中性灰阶、Calibrite ColorChecker Classic Mini 粘贴位。无需 gamepad_vla，也不控制机器人。许可证选择 MIT，见 `LICENSE`。

**v1.1 为推荐打印版本（审阅者裁决5）。正式外参必须固定相机，将板放在至少3个不同位置分别拍摄，并联合所有角点求解。单张图只能用于快速检查，不能作为正式外参。**

发布门槛：三位置联合相机误差≤2 mm、≤0.2°，重投影中位数≤0.5 px。三组联合测试3/3通过，最大误差0.632033 mm、0.051480°；原8种主档单图的重投影中位数8/8通过，最大0.094825 px。当前31项测试全部通过，检测、图案、噪声、模糊和数值阈值保持不变。

单图工作区投影仅供参考，不设门槛：最坏姿态平均0.761033 px、单点最大1.536273 px，历史1.0/0.5 px要求下0/8通过。单图相机误差最大3.850022 mm、0.223988°，同样只作诊断。全部原始值和旧门槛失败数据保留，见[裁决5发布报告](docs/v1_1/review5/report.md)、[当前测试](docs/v1_1/review5/pytest-run-1.txt)、[原始数值](docs/v1_1/review5/single-results.json)及[联合结果](docs/v1_1/review5/joint-results.json)。这是本地合成验证，实物打印验收和真实相机标定尚未执行。

**v1 已被 v1.1 取代，不要打印。** v1已移到 `superseded/`：白边仅2.25 mm且旧闭环依赖额外精化选择规则，原因见[归档说明](superseded/README.md)。v1.1采用5.5 mm白边与OpenCV标准流程。一手来源见[调研](docs/research.md)。

## v1.1 最终规格

规格唯一来源：`spec/board_v1_1.json`。所有版面坐标使用 **mm**，位姿工具平移使用 **m**。修改图案或排版后必须更新版本并重新生成、验证；检测必须使用对应规格。

| 项目 | 规格 |
|---|---|
| 板 ID / 版本 | STATION-CALIB-001 / 1.1.0 |
| 页面 | A3 横向 420×297 mm，MediaBox 按 72/25.4 pt/mm 固定 |
| ChArUco | 6×5 **格**，5×4 内角点，字典 DICT_4X4_50，marker ID 0–14 |
| 格边 / 标记边 | 50 / 39 mm，比例0.78，白边5.5 mm；每个 marker 含边框共6×6 cell |
| 图案尺寸 | 300×250 mm；图案左上角位于纸张左上角向右 25、向下 20 mm |
| 板坐标 | 图案左上外角为原点；面对印刷面 X 向右、Y 向下、Z 指入板内，右手系；OpenCV 非 legacy 模式 |
| 灰阶 | G1–G8，22×22 mm；名义 sRGB 为 (v,v,v)，v=16,48,80,112,144,176,208,240；名义值，不是实测反射率 |
| 色卡位 | 板坐标 (314,125) 起，63.5×109 mm，竖放；官方外形为 109×63.5 mm，不印彩色块 |
| X 校验尺 | (45,270) 到 (145,270)，100 mm |
| Y 校验尺 | (−12,40) 到 (−12,140)，100 mm |
| 安装孔 | 直径 3.2 mm 圆 + 总长 10 mm 十字线 + H1–H4 编号；只印定位标记，是否打孔由实际安装决定 |

灰阶左上角依次为 (317,15)、(342,15)、(317,41)、(342,41)、(317,67)、(342,67)、(317,93)、(342,93)。色卡局部坐标绕板 Z 轴转 +90°，精确齐次变换在 JSON 的 `colorchecker_slot.T_board_card_mm`。纸张、棋盘每个方格、每个 marker、每个内角点、灰阶、色卡框、孔、文字基线、尺和每条刻度的坐标均在 JSON 中。

| 孔号 | 板坐标中心 (X,Y) mm | 纸坐标（左上为原点）mm |
|---|---|---|
| H1 左上 | (−15,−10) | (10,10) |
| H2 右上 | (385,−10) | (410,10) |
| H3 右下 | (385,267) | (410,287) |
| H4 左下 | (−15,267) | (10,287) |

H1→H2 沿 +X，H2→H3 沿 +Y，顺时针编号。孔中心矩形 **400×277 mm**，两条对角线均 **486.54804 mm**（精确值以 JSON 为准）。孔心距纸边均 10 mm；自动检查圆、十字线及编号包围盒与棋盘、灰阶、色卡框、刻度尺的净距 ≥5 mm。

## 工作距离与可识别性

主档1280×720：fx=906.561、fy=905.986、cx=647.896、cy=362.233；备用640×480：fx=604.374、fy=603.991、cx=325.264、cy=241.489；D=0。完整输入在 `examples/camera_*.json`。

更新实测高度为0.70–0.75 m（±0.05 m），台面中心斜距约0.9 m。本次测试从最终变换复算高度、距离以及“板法线与视线夹角”和互余的“板面与视线夹角”，均记录于结果。中心及四周平移使用同一相机姿态，另测高低/远近边界。

39 mm标记的cell为6.5 mm。主档0.9 m、法线45°的最小采样量为3.53738 px（余量0.03738 px）；高度固定0.725 m时，采样量满足3.5 px的可行距离约0.8372–0.9813 m。白边5.5 mm，比OpenCV要求大于0.7 cell（4.55 mm）多0.95 mm，满足≥5 mm要求。全部一体式元素保留；首选排版已放下，未尝试6×4或5×4后备方案。净距数值见 `docs/v1_1/layout-check.json`。

可识别性按逐cell两个投影基向量的最小奇异值计算。中心与周围实际主档工况的采样量在指标中逐项列出；**整个0.65–0.80 m高度、0.8–1.0 m距离范围不能保证≥3.5 px**。较斜/较远时不足，满足条件的固定倾角距离边界见报告与 `docs/v1_1/design-check.json`。正式外参以至少3个位置的联合标定结果为准；单图工作区投影记录为参考。打印尺寸、对焦、反光与尺量误差仍须按实物验收检查。

## 本地环境与运行

已在本仓库 `.venv` 安装并验证；完整版本锁定在 `requirements.lock.txt`，直接依赖也在 `requirements.txt`。本次 Python 为 3.14.7；建议复现使用相同 Python 与 lock，其他 Python/平台未验证。不要在别的项目环境安装或混装另一份 OpenCV wheel。

```bash
cd /path/to/station_calib_board
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python -m pip check
.venv/bin/python -m calib_board.generate --spec spec/board_v1_1.json --output out/board_v1_1_A3.pdf
.venv/bin/python -m pytest -q --junitxml=docs/v1_1/review5/pytest-results.xml
```

生成器输出确定性矢量 PDF 和同名 **300 DPI** PNG 预览。棋盘、marker 的每一 cell 和灰阶均为矢量矩形；PNG 仅供查看，**打印 PDF**。PDF 纳入 Git 管理，`.venv` 和预览/合成图由 `.gitignore` 排除。

## 打印、贴板与验收

使用 A3 横向，**按实际尺寸 / 100% 打印，不要“适合页面”**。关闭应用和打印机驱动的缩放、自动适配及省墨模式，建议哑光纸。确认四角孔及页面边缘的尺均未被打印机裁切。

打印后先测量，再贴板：

1. 量 X、Y 两根 100 mm 刻度尺的端点中心，允许 99.5–100.5 mm。
2. 在棋盘中央与边缘分别量格边，50 mm 允许 49.75–50.25 mm；建议跨多个格量总长度后除以格数。
3. 量 H1–H2=400 mm、H1–H4=277 mm，并量 **H1–H3 和 H2–H4 对角孔中心距**，与 JSON 的 `hole_rectangle.diagonal_mm` 比较。各项相对偏差须 ≤0.5%。
4. 任一项偏差 >0.5% 判不合格，重新检查打印设置/打印机，勿直接拿名义尺寸求位姿。
5. 复制 `spec/print_measurements_v1_1.template.json` 为 `docs/measurements/<日期>_<板ID>.json`，记录打印机、纸张、尺具、各实测值、日期和验收人；模板空值表示未测，不能当作合格。把贴板后的复测、板厚与摆放测量一起记录。

用平整硬质底板，如 KT 板或亚克力；均匀粘贴，避免气泡、褶皱和翘曲，贴后复测。孔位只表示固定点，不要让螺钉、胶带或夹具侵入功能区。安装板厚和粘接层厚度一起计入“印刷面高出台面”的测量。

## 摆放和测量

推荐板平放、正面朝上，量 **H1、H2 两个孔中心**分别到台面后沿和左侧边的垂直距离。不要量纸角或孔外缘。长基线降低角度测量误差；换用任意另外两孔也支持，但须准确编号。

独立使用时定义台面局部世界系：原点在台面后沿与左侧边交点；X 从后沿指向前沿，Y 从左边指向右边，Z 向上，台面 Z=0。若与采集台既有 world 对接，其方向约定来自 gamepad_vla 的 `references/station_measurements.md`（2026-10-16 只读核对）：X 从立柱指向桌前沿，Y 从左侧指向右侧，Z 向上、地面 Z=0。记录中台面高度 767 mm。**本仓库不加载该项目**；用 `world_back_left_m` 显式填台面后左角在实际 world 中的 [X,Y,Z]。不要把台面 Z=0 与地面 Z=0 混用；台面高度也不是相机高度。X/Y 原点偏移须结合实际 world 定义测量，不能由高度推定。

测量输入（下面数值仅演示，非采集台实测）：

```json
{
  "hole_measurements": [
    {"id":"H1", "from_back_edge_mm":100, "from_left_edge_mm":200},
    {"id":"H2", "from_back_edge_mm":500, "from_left_edge_mm":200}
  ],
  "board_surface_above_table_mm":5,
  "world_back_left_m":[0,0,0],
  "distance_tolerance_mm":2
}
```

算法把各孔世界坐标写成 `(距后沿, 距左边, 印刷面高度)`，加上后左角偏移。设两孔板平面坐标差为 db，世界平面差为 dw，则 θ=atan2(dw.y,dw.x)+atan2(db.y,db.x)，板旋转列向量为 X=(cosθ,sinθ,0)、Y=(sinθ,−cosθ,0)、Z=(0,0,−1)。平移取两孔 `p_world − R p_board` 的平均。两孔间距与规格不一致超过默认 2 mm 时拒绝输入；该一致性检查不代表测量精度。只量两孔不能观测板翘曲或倾斜，算法明确假设板平放。板倾斜/竖放时，输入完整变换文件 `{"T_world_board": [[...],[...],[...],[0,0,0,1]]}`，平移单位 m。

每张图检测得到 `T_camera_optical_board`，求逆并组合：`T_world_camera_optical = T_world_board @ inv(T_camera_optical_board)`。输出 `pose_xyz_qw_qx_qy_qz` 即 **[x,y,z,qw,qx,qy,qz]**，四元数单位化，qw≥0；ROS optical 为 X 右、Y 下、Z 前，不额外引入 camera_link 旋转。

正式外参**强制使用同一固定相机、板放至少3个不同位置分别拍摄、角点联合求解**，例如台面中心及左右各约150 mm。相机、分辨率、焦距及内参保持不变。每个板位置都分别量孔中心并保存自己的摆放JSON，检测文件与摆放文件一一对应；不能给移动后的板复用同一摆放。

新 `--placements` 接口将各图角点经对应T_world_board变换到world后合并，统一调用solvePnP ITERATIVE和标准solvePnPRefineLM，得到一份T_world_camera_optical。全部角点等权，不剔点，不平均单图位姿。相机K/D、分辨率必须一致。留一整图后重新联合求解，输出jackknife标准差；一张图时为null。它只表示对所拍图像组的重复性，不包含内参、尺量、平面度、打印等系统误差。

旧 `--placement` 接口仅保留用于快速检查和兼容历史固定板数据，不作为正式外参流程。正式外参使用 `--placements`，至少3个不同位置；只输入单图时，CLI会打印“单张图只能用于快速检查，不能作为正式外参”的警告，同时输出检查结果。

## 工具示例

检测支持 JSON 的 K（3×3 或 9 个值）、D，以及 ROS `camera_info` YAML/JSON 的 `camera_matrix.data` / `distortion_coefficients.data`。使用与图像对应的分辨率和 OpenCV pinhole 畸变，支持 plumb_bob / rational_polynomial；不支持 fisheye。未自动缩放内参。

```bash
.venv/bin/python -m calib_board.detect /path/to/frame.png \
  --intrinsics /path/to/camera_info.yaml --spec spec/board_v1_1.json \
  --output out/detection.json --overlay out/detection_overlay.png

# 单图仅快速检查，会打印警告；不能作为正式外参
.venv/bin/python -m calib_board.extrinsics out/detection.json \
  --placement /path/to/measured_placement.json --output out/quick_check.json

# 固定相机，板中心/左/右三个位置；每个位置各自测量H1/H2并保存摆放
.venv/bin/python -m calib_board.extrinsics out/center_detection.json out/left_detection.json out/right_detection.json \
  --placements /path/to/center_placement.json /path/to/left_placement.json /path/to/right_placement.json \
  --output out/joint_extrinsics.json

# 必须至少3个不同位置；少于3个位置的结果不能作为正式外参

.venv/bin/python -m calib_board.gray_ramp /path/to/frame.png \
  --detection out/detection.json --output out/gray.json
```

检测输出角点 ID/像素坐标、物点、内参、板相对相机位姿和重投影误差中位数/P95（px），并保存坐标轴与角点叠加图。使用至少 6 个非共线角点，先用官方 CharucoDetector、matchImagePoints、solvePnP，再做 LM。标准参数固定为 marker `CORNER_REFINE_NONE`、`minMarkers=2`、`tryRefineMarkers=False`；ChArUco角点精化由OpenCV `detectBoard`内部完成。不再调用外部cornerSubPix，不做候选选择。PnP后的LM是标准位姿优化，不重新精化/筛选角点。裁决5的发布门槛为至少3个位置联合相机误差≤2 mm / 0.2°，重投影中位数≤0.5 px。单图工作区投影、单图平移与旋转仅作参考，数值完整保留。

灰阶工具按位姿投影每块中央 60% 区域中的 20×20 网格，双线性采样平均 RGB（输出为 RGB 顺序，8 bit），越界块标为不可用；假设被采样块未被遮挡。用无明显截断的中间名义灰阶估计 `[G/R,1,G/B]` 白平衡增益，检查亮度顺序、≥250 高光截断、≤5 暗部压黑，并报告码值直线拟合残差。打印、照明和相机响应都影响结果，名义灰阶不是实测反射率，这些结果不能证明辐射线性，**不是完整颜色校正**。

拍摄时使用均匀漫射光，避免反光与阴影，保持清晰对焦，锁定分辨率、焦距和内参。做内参标定时应覆盖画面不同区域和适度倾角；本工具只用已知内参求外参，不估计内参。移动相机或改变镜头后重新标定。

## 采集台副本

采集台使用目录：`~/calibration_board/`。v1.1副本包含PDF、规格、打印验收模板、README、许可证、实测内参JSON，以及检测与多位置外参所需Python模块。v1旧PDF、规格、README和脚本保留在该目录的 `superseded/`，归档说明明确不要打印。

副本不含开发环境、生成器、pytest、合成图或灰阶分析模块；完整工具与历史报告在本仓库。上方环境创建/生成/测试/灰阶命令适用于完整仓库。副本中检测和联合外参可使用已准备好OpenCV/numpy/PyYAML的解释器，从该目录运行 `python -m calib_board.detect ...` 和 `python -m calib_board.extrinsics ...`；先按每个位置实测孔中心保存摆放文件。

本次发布只用shell/mkdir/mv/tar在 `~/calibration_board/` 内归档和复制，并读回文件核对；不在采集台执行标定程序或安装依赖。传输结果见完整仓库的 `docs/v1_1/review5/copy-result.txt`。
