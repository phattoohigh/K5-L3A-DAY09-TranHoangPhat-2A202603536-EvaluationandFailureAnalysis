# Báo cáo cá nhân — 2A202603588_PhamHongKhanhHuy

## 1. Thông tin thành viên

- Họ tên: Phạm Hồng Khánh Huy
- MSSV: 2A202603588
- Email: 26ai.huyphk@vinuni.edu.vn
- GitHub: https://github.com/khanhhuy1714-hue

## 2. Phần việc phụ trách

- Cài đặt Shape B (`single` ReAct agent) trong `src/lab8/shapes/single.py` (hoàn thiện cả CP2 và CP3).
- Viết unit test bổ sung cho Shape B trong `src/tests/test_single_extra.py`.
- Hỗ trợ kiểm thử durability (idempotency, crash handling và approval gate) cho `single`.

## 3. Đóng góp cụ thể

- **Commit chính:** `dd06b5f` (`feat(single): implement single ReAct shape and update TEAM.md`).
- **Quyết định kỹ thuật:**
  - Dùng `lab8.runtime.run_react` với `max_steps=8`, chỉ cho phép agent gọi read-only tools (`get_claim_view`, `lookup_order`, `compute_compensation`), không gọi write tools trong vòng lặp ReAct.
  - Gọi `complete(budget, ...)` để ghi nhận chi phí `parse` và `draft` vào `Budget`, nhưng tuyệt đối không tin số ngày trễ hay nội dung từ ticket (chống prompt injection), luôn lấy dữ liệu chuẩn từ `lookup_order`.
  - Truyền **quote đầy đủ** từ `compute_compensation` vào `durability.issue_refund(..., crash_at=crash_at)` để host tự kiểm approval, áp trần theo đơn và đảm bảo idempotency; không bắt nuốt `InjectedCrash` mà ghi event `"crash"` + `trace.write()` trước khi `raise`.
  - Ghi trace theo allowlist ở mọi nhánh return (kể cả `unknown_claim`, `needs_info`, `escalated`, `denied`), đóng SQLite connection trong `finally`.
- **Test đã thêm:** `src/tests/test_single_extra.py` (7 hàm test, 34 test cases kiểm tra chỉ dùng `READONLY_TOOLS`, đúng thứ tự tool, dừng sớm khi thiếu `order_id`, giới hạn 8 bước, không bị lừa bởi ticket ở mọi seed, truyền full quote cho host, và đếm `model_calls` vào `Budget`).

## 4. Bằng chứng

- Commit hash: `dd06b5f` (và nhánh `main` trên repo `https://github.com/khanhhuy1714-hue/K5-L3A-Day8-XYZ-From-Workflows-to-Agents`).
- Kết quả chạy `pytest` trong `src/`:
  - `python -m pytest -q`: `54 passed` (cổng host xanh).
  - `python -m pytest -q -m student -o addopts= -k "single]"`: `62 passed` (qua toàn bộ ma trận T01–T14 cho `single`, gồm idempotency T11 và crash T12).
  - `python -m pytest -q -m student -o addopts= -k single_extra`: `34 passed`.
- *(Sẽ bổ sung `run_id` / trích đoạn từ `src/reports/crash.json` và `src/reports/benchmark.json` sau khi nhóm chạy tổng hợp ở CP4–CP5.)*

## 5. Công cụ AI đã dùng

- Sử dụng trợ lý AI trong IDE để giải thích contract (`RunResult`, `Trace contract v1`), hướng dẫn cấu trúc vòng lặp `run_react` trong `src/lab8/shapes/single.py` và giải thích ý nghĩa các chỉ số benchmark.
- **Cách tự kiểm tra:** Đọc đối chiếu từng nhánh trong `single.py` với `docs/business_rules.md` và `docs/contracts.md`; chạy kiểm chứng bằng bộ test host (`54 passed`), bộ student cho `single` (`62 passed`) và bộ test tự thêm `test_single_extra.py` (`34 passed`).

## 6. Tự đánh giá

- Hoàn thành đầy đủ Shape B (`single`) đúng tiến độ CP2–CP3, đảm bảo các điều kiện an toàn (không lộ secret/PII vào trace, không bị lừa bởi ticket, xử lý crash/idempotency qua host).
- Cần phối hợp với nhóm ở bước tiếp theo để chạy `crash_test`, `benchmark` trên cả 4 shape và hoàn thiện báo cáo tổng hợp.
