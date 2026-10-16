# 一手资料调研与设计依据

查阅日期：2026-10-16。仅引用项目官方文档、官方源码和厂商资料。本文区分上游事实、本仓库的选择和仍需实物验证的内容。

## OpenCV 4.7 以后的 API

[官方 ChArUco 教程（4.13.0）](https://docs.opencv.org/4.13.0/df/d4a/tutorial_charuco_detection.html)说明构造参数为 X/Y 格数、格边、marker 边和字典；推荐用 `matchImagePoints` 与 `solvePnP` 求位姿。[CharucoDetector Python API](https://docs.opencv.org/4.13.0/d9/df5/classcv_1_1aruco_1_1CharucoDetector.html)给出 `CharucoDetector(board, charucoParams, detectorParams)` 和 `detectBoard(image)` 返回角点、角点 ID、marker 及 marker ID。可通过 CharucoParameters 传 K/D。

本仓库实际使用 Python wheel 4.13.0.92，运行时 cv2.__version__=4.13.0：`cv2.aruco.CharucoBoard((7,6), .044, .0395, dictionary)`、`CharucoDetector`、`generateImageMarker`。官方说明 4.6 前后存在坐标/偶数行图案兼容变化；本规格明确 `setLegacyPattern(False)`，不用旧 `CharucoBoard_create`。原点和轴以当前 API 返回的物点与实际 PDF 检测闭环验证，固定为印刷面图案左上角 X 右、Y 下、Z 向内。

标记位模式取自 OpenCV 预定义字典，生成 6×6（4×4 数据加每边一层黑边）位图数组，仅将数组的每一位作为 PDF 矢量矩形绘制；PDF 不嵌入数组图像。

## DROID 的参照参数

[DROID 标定指南](https://droid-dataset.github.io/droid/example-workflows/calibrating-cameras.html)介绍 ChArUco 位姿可视化与标定工作流，但不直接列格边等参数。追到官方代码：[参数定义](https://github.com/droid-dataset/droid/blob/main/droid/misc/parameters.py#L17-L21)为 **14 列×9 行、20 mm 格、16 mm marker、DICT_5X5_100**；[标定代码](https://github.com/droid-dataset/droid/blob/main/droid/calibration/calibration_utils.py#L13-L20)读取这些常量构板，使用旧版 API。

这些是参照，不是本板规格。本仓库不复制 DROID 标定程序或其环境，不假定不同字典/尺寸兼容。官方 main 的参数页面和原始文件已查阅；main 是浮动链接，本报告的参数摘录记录本次观察。

## calib.io 关于尺寸、打印与支撑

[Calibration Best Practices](https://calib.io/blogs/knowledge-base/calibration-best-practices)建议在工作距离对焦，覆盖不同区域与倾角，使用漫射照明、刚性支撑，检查逐点重投影误差，并指出低重投影误差不等于高标定精度。厂商在同页回复中建议图像中的方格通常不小于约 20×20 px；这是经验建议，不是我们的 3.5 px/cell 验收条件。

[官方图案生成器说明](https://calib.io/pages/camera-calibration-pattern-generator)要求关闭打印缩放与驱动光栅化，并建议打印后实测。本任务用自己的 OpenCV/reportlab 生成器，不使用其有使用限制的生成器输出。普通打印的误差、平整度仍需实测；本次合成测试不能验证打印机、纸张或硬板质量。

## Calibrite Classic Mini 官方尺寸

[Calibrite 官方产品页](https://calibrite.com/us/product/colorchecker-classic-mini/?noredirect=en-US)的描述和技术规格均列出 **63.5×109.0 mm**，24 个色块。预留位选择外形等大的 **63.5 mm 宽×109 mm 高**竖框；不复制其专有色块，不将普通打印灰阶称为标准反射率目标。

## 本仓库的选择与验证方案

选择 **7×6 格、44 mm 格边、39.5 mm marker、DICT_4X4_50**，获得 6×5 个内角点。44 mm 格边在当前版面中保留上方文字、下方尺及其与棋盘至少 3 mm 间隙；继续增加格边会压缩这些间隙或侵占旁侧功能区。全部功能均保留，没有按取舍优先级删除任何项目。

4×4 字典在相同 marker 外形下用 6 cell，5×5 用 7 cell；较少的编码量与较小字典降低区分容量，选择 4×4 是为工作距离下的成像采样量。两种字典都可能误检；不声称换字典就能防止其他 4×4 板干扰。使用唯一板 ID/规格、空间一致的多个 ChArUco 角点和重投影检查；同视场尽量只放一块该规格板。没有做字典误检率实测，也没有把经验判断写成概率。

设计实验：固定纸张、格数、marker 外形和 K，只改变字典，按实际板几何投影 cell 的相邻顶点；以局部两个投影基向量矩阵的最小奇异值衡量最强压缩方向。板中心位于光轴，距离指相机到图案中心；法线夹角 45°，倾斜方位每 5° 扫描一周，取全体 marker、全体 cell 的最小值。主档 0.9 m 下，4×4 为 **3.525886 px**，5×5 对照为 **3.019341 px**，后者不达 3.5 px。实际计算见 `design-check.json`，程序在 `calib_board/synthetic.py`。

备用档 0.8 m、45° 下为 **2.558797 px**，不达尽量 3 px 的目标；二分距离求得约 **0.632 m** 的 3 px 边界。主档对应 3.5 px 边界约 0.909 m。这是离散方位扫描下的几何预算，不是连续方位的形式化证明或真实检测率。1.0 m、60° 法线夹角等情况的采样量单列于报告。

39.5 mm marker 的白边 2.25 mm，小于 OpenCV 的 0.7 cell（约 4.61 mm）建议。此权衡已通过固定种子、实测 K、真实距离、轻微模糊/噪声/遮挡的合成实验，但实际打印与相机图像尚未验证。后续最小实拍验证：固定相机分辨率和曝光，按 0.6/0.8/0.9/1.0 m、法线夹角 30/45/60° 各采同数量图像，记录检测成功率、角点数、误差和尺量参考位姿；增加倾角/距离后若检测显著退化则支持采样量不足解释。若近距离同样失败，应先查打印尺寸、对焦和光照。本次没有执行该实拍实验。

许可证由本项目选择 **MIT**；不改变 OpenCV、ReportLab、PDFium 等依赖的上游许可证。

## v1.1 更新（2026-10-16；前文为v1历史）

v1已经被v1.1设计取代，不要打印；v1.1标准流程闭环失败，目前也暂不要打印，见 `v1_1/report.md`。首选6×5格、50 mm格边、39 mm标记，比例0.78，白边5.5 mm。官方ChArUco教程上述链接的“Detection”部分明确要求白边大于0.7个module；本字典含边框6 cell，所以下限4.55 mm。本方案多0.95 mm，满足用户≥5 mm要求。官方并没有统一指定比例0.75–0.8；这是用户的设计范围，官方白边条件在本字典下换算成M/S<0.81081。

同一官方教程说明marker精化建议关闭、ChArUco角点插值后内部做亚像素精化。本次明确使用CORNER_REFINE_NONE、minMarkers=2、tryRefineMarkers=False，保留OpenCV内部默认角点精化和标准PnP/LM；删除v1外部cornerSubPix和10%RMS选择规则。没有在标准流程失败后继续挑参数。
