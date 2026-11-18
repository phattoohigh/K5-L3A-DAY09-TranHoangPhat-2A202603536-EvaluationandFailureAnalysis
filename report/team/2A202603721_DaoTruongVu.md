# Báo cáo cá nhân — 2A202603721_DaoTruongVu

## 1. Thông tin thành viên

- Họ tên: Đào Trường Vũ
- MSSV: 2A202603721
- Email: 26ai.vudt@vinuni.edu.vn
- GitHub: emvuthosan

## 2. Phần việc phụ trách

Nhiệm vụ: Ledger / crash, evaluation và báo cáo.

- Test cho phần host (approval, trần tiền, idempotency, crash) và bộ kịch bản giống hidden chạy trên cả ba shape của nhóm.
- Sinh bằng chứng trong `src/reports/`: crash suite, benchmark 4 shape × 5 seed, ablation cho research card.
- Viết `report/team/decision_adr.md`, `report/team/research_card.md`, `report/team/group_report.md`; điền `TEAM.md`.

## 3. Đóng góp cụ thể

- `src/tests/test_host_edge_cases.py` (21 test, chạy trong cổng host `python -m pytest -q`):
  - approval hết hạn, thiếu, trỏ tới approval không tồn tại, trạng thái `revoked` / `pending` / `rejected`, approval 0 đồng, quote ≤ 0;
  - trần theo approval, trần theo số đã trả, top-up bị chặn bởi approval;
  - test chứng minh vì sao shape phải truyền quote đầy đủ: nếu tự trừ trước thì T14 ghi 90.000 thay vì 120.000;
  - thiếu đơn, đơn của principal khác, claim không tồn tại;
  - xung đột số tiền lặp lại vẫn giữ số đã commit và chỉ audit một lần;
  - ba điểm crash (`before_effect`, `after_effect_before_checkpoint`, `after_checkpoint`), resume bằng kết nối mới.
- `src/tests/test_shapes_adversarial.py` (243 test, marker `student`): 13 kịch bản giống bộ hidden × 5 seed × 3 shape: ticket nói dối, injection, đơn hủy / đang giao / phí ship 0, approval thu hồi / mượn / thiếu, homoglyph, mã đơn chỉ có trong ticket, principal lẫn, ship + hỏng hàng cùng đủ điều kiện, trần hỏng hàng theo số đã trả. Thêm quét secret / PII trên 14 claim public, claim không tồn tại, và kiểm tính tất định theo seed.
- Quyết định kỹ thuật: chọn `workflow` trong ADR. Ba shape cùng pass 1.000 trên public, workflow có cost/success thấp nhất (28.79 VND) và ít tự chủ nhất. Research card chọn R1 và ablation bật/tắt lớp investigator (workflow so với orchestrator).
- Commit chính:

## 4. Bằng chứng

- `src/reports/crash.json`: `crash_safety` = `20/20`.
- `src/reports/benchmark.json`: workflow / single / orchestrator pass 1.000, pass^5 1.000; swarm 0.986 / 0.929, fail duy nhất `R-swarm-C-002-s55`.
- `src/reports/ablation_r1.json`: cost/success 28.79 → 57.19 VND, tool call mỗi trial 2.79 → 5.57 khi thêm lớp investigator; pass rate không đổi.
- Lệnh tự kiểm: `python -m pytest -q` (75 passed), `python -m pytest -q -m student -o addopts=` (554 passed), `python -m lab8.check_submission`.
- Kiểm chéo bộ kịch bản hidden-style: chạy tạm cùng bộ đó trên swarm cho đúng một fail (`C-ADV-LIE` seed 55), nên test bắt được lỗi thật chứ không pass vô điều kiện.

## 5. Công cụ AI đã dùng

- **Claude Code** (trợ lý lập trình): Hỗ trợ đọc repo và docs, hỗ trợ viết hai file test của tôi, chạy smoke / pytest / crash suite / benchmark / ablation, viết nháp ADR, research card và gợi ý nội dung để tôi viết báo cáo nhóm. 

## 6. Tự đánh giá
Không

