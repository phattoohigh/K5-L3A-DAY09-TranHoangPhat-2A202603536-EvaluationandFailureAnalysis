# Team

## Thông tin nhóm

- Tên nhóm: XYZ
- Lớp: L3A
- Repo nhóm: `K5-L3A-Day8-XYZ-From-Workflows-to-Agents`
- URL repo, nhánh nộp, commit chốt: https://github.com/khanhhuy1714-hue/K5-L3A-DAY08-XYZ-FromWorkflowsToAgents.git

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
|   1 | Vũ Lê Hoàng | 2A202603542   |   26ai.hoangvl@vinuni.edu.vn    |        | Shape A workflow + integration |
|   2 | Phạm Hồng Khánh Huy | 2A202603588     |    26ai.huyphk@vinuni.edu.vn   |        | Shape B single ReAct |
|   3 | Trần Hoàng Phát |   2A202603536   |   26ai.phatth@vinuni.edu.vn    |        | Shape C orchestrator + handoff |
|   4 | Đào Trường Vũ | 2A202603721 |    26ai.vudt@vinuni.edu.vn   |        | Ledger/crash, evaluation, benchmark, ADR, research card, báo cáo nhóm |

## Bảng đóng góp

`python -m lab8.check_submission` đọc bảng này bằng máy: giữ nguyên tiêu đề `## Bảng đóng góp` và các cột. Mỗi người một dòng: commit có nội dung và ít nhất một test đã thêm hoặc sửa.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| Vũ Lê Hoàng | Shape A workflow | `a65cc49` feat(workflow): implement shape A deterministic workflow | `src/tests/test_workflow_extra.py` |
| Phạm Hồng Khánh Huy | Shape B single | `dd06b5f` feat(single): implement single ReAct shape | `src/tests/test_single_extra.py` |
| Trần Hoàng Phát | Shape C orchestrator | `1eb057a` implement orchestrator shape with safe handoff | `src/tests/test_orchestrator_extra.py` |
| Đào Trường Vũ | Ledger, evaluation, report | | `src/tests/test_host_edge_cases.py`, `src/tests/test_shapes_adversarial.py` |

## Cá nhân

Mỗi thành viên đồng thời tạo một báo cáo riêng trong `report/` theo dạng:

```text
report/team/MSSV_HoTen.md
```

Ví dụ: `report/team/20241234_NguyenVanAn.md`.

Sao chép mục dưới đây cho từng thành viên.

## 2A202603588_PhamHongKhanhHuy

### Phần việc phụ trách

- Cài đặt Shape B (`single` ReAct agent) trong `src/lab8/shapes/single.py` (CP2 & CP3).
- Viết unit test bổ sung cho `single` trong `src/tests/test_single_extra.py`.

### Đóng góp cụ thể

- Cài đặt vòng lặp `run_react(..., max_steps=8)` chỉ dùng read tools (`get_claim_view`, `lookup_order`, `compute_compensation`), chống prompt injection từ ticket, truyền full quote vào `durability.issue_refund`, giữ nguyên `InjectedCrash` và ghi trace đúng contract.
- Thêm `src/tests/test_single_extra.py` (34 test cases kiểm tra `READONLY_TOOLS`, 8-step cap, prompt injection, full quote, và `Budget`).

### Bằng chứng

- Commit `dd06b5f` (`feat(single): implement single ReAct shape and update TEAM.md`).
- `python -m pytest -q`: `54 passed`.
- `python -m pytest -q -m student -o addopts= -k "single]"`: `62 passed`.
- `python -m pytest -q -m student -o addopts= -k single_extra`: `34 passed`.

## MSSV_HoTen

### Phần việc phụ trách

-

### Đóng góp cụ thể

-

### Bằng chứng

-
