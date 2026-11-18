# Báo cáo cá nhân — 2A202603536_TranHoangPhat

## 1. Thông tin thành viên

- Họ tên: Trần Hoàng Phát
- MSSV: 2A202603536
- Email: 26ai.phatth@vinuni.edu.vn
- GitHub: phattoohigh

## 2. Phần việc phụ trách

Phụ trách Shape C — orchestrator trong `src/lab8/shapes/orchestrator.py` và bộ test bổ sung
`src/tests/test_orchestrator_extra.py`. Hai shape A (workflow) và B (single agent) do các thành
viên khác thực hiện song song.

Shape C tổ chức luồng xử lý theo mô hình orchestrator và investigator:

1. Orchestrator đọc claim qua view đã giới hạn field.
2. Orchestrator tạo handoff `handoff.v1` bằng `make_handoff`, không chuyển parent context.
3. Investigator chỉ được gọi các tool đọc để kiểm tra order, policy, lịch sử refund và tính quote.
4. Orchestrator nhận full quote và gọi `durability.issue_refund`; investigator không có quyền ghi.
5. Host kiểm approval, giới hạn theo order, idempotency và crash recovery trước khi ghi ledger.

## 3. Đóng góp cụ thể

- Hoàn thiện `run_claim` cho Shape C với đúng chữ ký chung của bốn kiến trúc.
- Xử lý đủ các trạng thái `failed`, `needs_info`, `escalated`, `denied` và `resolved`.
- Dùng handoff allowlist với các tool `lookup_order`, `lookup_policy`,
  `lookup_refund_history` và `compute_compensation`.
- Không đưa ticket, secret, raw header, thông tin cá nhân hoặc parent context vào handoff/trace.
- Truyền full quote cho host để tránh trừ refund cũ hai lần trong case top-up T14.
- Truyền `crash_at` vào `issue_refund` và để `InjectedCrash` propagate cho crash test.
- Thêm 13 test cho ranh giới handoff, worker read-only, chống lộ PII, không gọi host khi
  không có entitlement và kiểm tra full quote.
- Commit Shape C: `1eb057a` (`implement orchestrator shape with safe handoff`).
- Commit test và báo cáo cá nhân sau rebase: `20bba74`
  (`add orchestrator tests and Tran Hoang Phat report`).

## 4. Bằng chứng

- Code: `src/lab8/shapes/orchestrator.py`.
- Test: `src/tests/test_orchestrator_extra.py`.
- File test nguồn: `/Users/phat/Downloads/test_orchestrator_extra.py`.
- Lệnh test riêng:
  `python -m pytest -q -m student -o addopts= -k orchestrator_extra`.
- Kết quả test riêng: `13 passed, 302 deselected`.
- Lệnh kiểm tra toàn bộ Shape C:
  `python -m pytest -q -m student -o addopts= -k orchestrator`.
- Kết quả toàn bộ Shape C: `75 passed, 240 deselected`.
- Run ID tiêu biểu: `R-orchestrator-C-014-s11`.
- Case T14: full proposal là 150.000 VND; host ghi phần chênh 120.000 VND sau khi tính
  30.000 VND đã hoàn trước đó.

## 5. Công cụ AI đã dùng

Đã dùng Codex để đọc contract, luật nghiệp vụ, implementation swarm tham chiếu, hỗ trợ hoàn
thiện Shape C và rà soát ranh giới bảo mật. Kết quả được tự kiểm tra bằng bộ test bổ sung và
toàn bộ ma trận student dành cho orchestrator. Không dùng AI để tạo số liệu benchmark, run id
giả hoặc thay đổi các file thước đo của đề bài.

## 6. Tự đánh giá

Phần Shape C đã đáp ứng các yêu cầu chính: investigator chỉ đọc, handoff được sanitize,
orchestrator là bên duy nhất yêu cầu host ghi refund, full quote được giữ nguyên, trace không
chứa secret/PII và cơ chế retry/crash dùng durability của host. Kết quả hiện tại qua toàn bộ
75 test liên quan đến orchestrator trong bộ test đang có.
