# Phase 4 Windows 同Hash文件并发失败与修复

## 实际失败记录

执行日期：2026-10-11。本条记录来自本次真实离线测试的**工具返回摘录**，不是完整stdout日志；没有将摘录重造为完整运行日志。下面的临时目录路径已脱敏。

执行目录：`D:\京剧\京剧`。

实际命令：

```powershell
.\.venv\Scripts\python.exe -m pytest -q backend/tests/test_phase4_assets.py backend/tests/test_phase4_styles.py backend/tests/test_phase4_neural4d.py backend/tests/test_phase4_usage.py
```

该次运行退出码：1。工具返回的最终结果：

```text
FAILED backend/tests/test_phase4_assets.py::test_generated_model_registration_atomic_under_concurrent_retrievals
1 failed, 190 passed, 1 warning in 27.62s
```

实际失败调用链摘录：

```text
test_generated_model_registration_atomic_under_concurrent_retrievals
  ids = [job.result()['modelId'] for job in jobs]
register_generated_model
  'storageKey': self.save_bytes('models', raw, validation['hash'], 'glb')
save_bytes
  os.replace(temporary_path, destination)
PermissionError: [WinError 5]
```

失败发生于临时离线资产目录中的 `.part` 文件发布到同Hash `.glb` 路径。这个测试并发执行4次同一离线供应商结果登记。文件层反复替换同一Hash文件；Windows存在其他读取者时，`os.replace` 可能被拒绝。SQLite的同供应商任务ID去重没有消除文件层冲突。

这次失败不应被此前的通过结果覆盖；它揭示了此前测试未稳定复现的真实并发问题。测试中的程序化四面体、Agent任务容器和供应商任务ID均为明确的离线夹具，没有真实Neural4D调用或新LLM输出。

## 修复

仅调整资产服务的文件发布方式：

- 内容Hash文件已经存在时，核对长度和SHA256后复用原文件，不进行替换。
- 如果已有文件损坏，拒绝并要求人工核查，不以自动重写掩盖损坏。
- 新文件先写入同目录临时文件并flush/fsync，再用原子、不覆盖的硬链接发布。
- 并发发布发现目标已存在时，核对并复用赢家文件；清理本次临时文件。

新增测试覆盖：已有文件正在被读取时重复保存、不自动修复篡改文件、8线程同时发布同Hash文件、无残留临时文件。原有4线程供应商结果登记去重测试继续保留。

该修复不改变模型、图像或文化版本内容，不修改配额、真实任务或Phase 3数据库。硬链接要求部署文件系统支持该操作；本次验收环境是Windows本地文件系统，不承诺未验证文件系统上的可用性。

## 修复后验证记录

使用上方相同命令实际重新运行，退出码为0，工具返回最终结果：

```text
193 passed, 1 warning in 22.94s
```

该次运行包含旧真实Phase 3结果的脱敏导出兼容性回归，以及新增2项文件发布测试。4线程供应商结果登记、8线程同Hash发布、打开文件时复用和拒绝自动覆盖损坏内容均实际通过。

警告为现有Starlette/TestClient关于httpx弃用的提示，不是测试失败。193项为这4个Phase 4后端测试文件的结果，不代表整个项目最终全量验收；最终全量回归另行执行和记录。未执行供应商API、付费请求或真实建模。
