# Báo cáo nhóm — Lab 8 LogiX-VN
## 1. Thông tin nhóm

- Tên nhóm: XYZ
- Thành viên: xem `TEAM.md`
- Commit chốt (trùng `report/team/decision_adr.md`):

## 2. Mục tiêu và cách tiếp cận

Bài toán: xử lý claim hoàn phí vận chuyển của LogiX-VN bằng bốn kiến trúc có cùng chữ ký `run_claim`, rồi chọn kiến trúc ít tự chủ nhất mà vẫn đúng. Nhóm hiểu ranh giới cốt lõi trước khi viết code: số tiền do `compute_compensation` tính; approval, trần theo đơn và idempotency do host (`durability.issue_refund`) quyết. 

Chia việc cho 4 người:

| Phần | File | Người |
| --- | --- | --- |
| Shape A workflow + integration | `src/lab8/shapes/workflow.py`, `src/tests/test_workflow_extra.py` | Vũ Lê Hoàng |
| Shape B single ReAct | `src/lab8/shapes/single.py`, `src/tests/test_single_extra.py` | Phạm Hồng Khánh Huy |
| Shape C orchestrator + handoff | `src/lab8/shapes/orchestrator.py`, `src/tests/test_orchestrator_extra.py` | Trần Hoàng Phát |
| Ledger, crash, evaluation, báo cáo | `src/tests/test_host_edge_cases.py`, `src/tests/test_shapes_adversarial.py`, `src/reports/`, `report/team/` | Đào Trường Vũ |

Thứ tự: workflow trước (đơn giản nhất, làm mẫu cách dùng `finish()` và `Trace`), rồi single và orchestrator song song. Swarm có sẵn, chỉ dùng để đối chứng. Phần ledger/evaluation viết test cho host song song với ba shape, vì các test này không phụ thuộc shape.

## 3. Giải pháp

**A — workflow.** Các bước Python cố định: `get_claim_view` (không `SELECT *`) → thiếu `order_id` thì `needs_info` → `lookup_order` theo principal; không thấy hoặc không sở hữu thì `escalated` → `compute_compensation` từ order row, bỏ qua số ngày trong ticket → quote 0 thì `denied`, không gọi host → quote > 0 thì gọi `issue_refund(conn, claim_id, <quote đầy đủ>, crash_at=crash_at)`. Host từ chối thì `denied` (host ghi `policy_denied`), xung đột số tiền thì `failed`, thành công thì `resolved`. MockLLM chỉ được gọi một lần để soạn câu trả lời.

**B — single ReAct.** `runtime.run_react` với `max_steps=8`. `decide()` chỉ chọn tool đọc theo thứ tự `get_claim_view` → `lookup_order` → `compute_compensation`, rồi trả `final` với quote. Model đọc ticket (`purpose="parse"`) để tính chi phí, nhưng không dùng số trong ticket. Sau vòng lặp, chính code của shape gọi `issue_refund`; model không có quyền ghi.

**C — orchestrator.** Orchestrator đọc claim view, dựng handoff bằng `make_handoff` với `facts={}` và allowlist tool chỉ đọc (`lookup_order`, `lookup_policy`, `lookup_refund_history`, `compute_compensation`). `run_readonly_investigators` chạy các tool đó; investigator không có registry ghi. Orchestrator quote từ order view mà investigator trả về và gọi `issue_refund` với quote đầy đủ. Trace ghi handoff đã sanitize, không ghi parent context.

**Ranh giới code / model** (theo [docs/architecture.md](../../docs/architecture.md)): ở cả ba shape, tiền, approval, trần, idempotency và ghi ledger nằm trong code/host. Model chỉ soạn chữ (A), chọn tool đọc trong bound 8 bước (B), hoặc lập kế hoạch (C).

**Vì sao truyền quote đầy đủ.** Host tự trừ phần các claim khác đã nhận trên cùng đơn. Shape tự trừ trước thì host trừ thêm lần nữa: test `test_shape_that_subtracts_prior_refund_itself_underpays` cho thấy T14 sẽ ghi 90.000 thay vì 120.000.

**Trace.** Mọi nhánh return đi qua `finish()`, nên luôn có `traces/<run_id>.json` đúng contract v1. Nhánh crash ghi event `crash` và `trace.write()` trước khi ném lại `InjectedCrash`. Không shape nào ghi ticket, `parent_secret`, header hay order row thô.

## 4. Kết quả

Bộ public, 14 claim × seed 11, 22, 33, 44, 55, mỗi trial một SQLite mới (`src/reports/benchmark.json`):

| Shape | Pass rate | Pass^5 | Seed min–max | Variance | Cost/success (VND mô phỏng) | Mean / p95 steps | Model call / trial | Tool call / trial |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: |
| workflow | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 28.79 | 3.79 / 4 | 1.0 | 2.79 |
| single | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 29.28 | 2.79 / 3 | 2.0 | 2.79 |
| orchestrator | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 57.19 | 3.43 / 4 | 2.0 | 5.57 |
| swarm | 0.986 | 0.929 | 0.929–1.000 | 0.000816 | 49.57 | 2.80 / 3 | 3.0 | 4.66 |

Swarm fail đúng một trial (`R-swarm-C-002-s55`: `status resolved != denied`). Đây là điểm yếu cố ý: ở seed 55 swarm tin "trễ 5 ngày" trong ticket thay vì `delay_days = 2`.

- **Crash safety:** `20/20` (`src/reports/crash.json`). T12 (crash sau khi ghi effect, trước checkpoint, rồi resume) xanh trên cả ba shape.
- **Cổng host:** `python -m pytest -q` ra 75 passed (54 test có sẵn + 21 test nhóm thêm).
- **Ma trận student:** 248/248 passed (62 test × 4 shape).
- **Kịch bản giống hidden** (`src/tests/test_shapes_adversarial.py`, nhóm tự dựng): 13 kịch bản × 5 seed, cộng quét leak trên 14 claim public, claim không tồn tại và kiểm tính tất định. Kết quả 243/243 passed trên ba shape. Kiểm chéo: cùng bộ này chạy trên swarm bắt được đúng một fail (`C-ADV-LIE` seed 55), nên test có khả năng phát hiện lỗi thật.
- **Tự kiểm trên `student_drop/`:** chưa chạy. Lúc viết báo cáo nhóm chưa nhận thư mục này.

Quyết định kiến trúc và lý do: xem `report/team/decision_adr.md`. Phiếu nghiên cứu và ablation: xem `report/team/research_card.md`.

## 5. Khó khăn và cách xử lý

- **`py` không có trên một máy Windows.** Lệnh `py -3 -m venv .venv` báo `The term 'py' is not recognized`. Cách xử lý: dùng `python -m venv .venv` (Python 3.11.9), rồi gọi `.\.venv\Scripts\python.exe` trực tiếp. Sau đó smoke in `lab8.smoke pass` và cổng host xanh.
- **Hiển thị tiếng Việt trong PowerShell 5.1.** `Get-Content` không chỉ định encoding làm file markdown UTF-8 hiện thành ký tự lỗi. File không bị hỏng; đọc bằng editor hoặc `Get-Content -Encoding UTF8` thì đúng. Nhóm không sửa file nào bằng `Set-Content` để tránh ghi sai encoding.
- **Test phải có tác dụng thật, không chỉ xanh.** Để chắc bộ kịch bản hidden-style không pass vô điều kiện, nhóm chạy tạm cùng bộ đó trên swarm. Nó fail đúng chỗ swarm có điểm yếu, rồi nhóm xóa bản chạy tạm.

## 6. Tổng hợp đóng góp

Chi tiết đóng góp của từng thành viên nằm trong `TEAM.md` (bảng đóng góp) và báo cáo cá nhân `report/team/MSSV_HoTen.md`.

## 7. Hạn chế và hướng cải thiện

MockLLM không phải model sản xuất; latency là `unavailable`. MockLLM cố định theo seed và không hiểu sai ngôn ngữ như một LLM thật, nên variance 0 của ba shape không chứng minh single hay orchestrator sẽ ổn định với model thật. Giá là mô phỏng theo `config/pricing.yaml`. Kết luận dựa trên 14 claim public và 13 kịch bản nhóm tự dựng; pass rate trên 40 claim hidden do grader giảng viên chấm.

Điều kiện làm kết luận thay đổi: ticket mơ hồ thật sự cần model chọn bước (nghiêng về single); nhiều nguồn dữ liệu độc lập cần gọi song song (nghiêng về orchestrator); hoặc hidden lộ trường hợp workflow cứng không xử lý được.

Hướng cải thiện: tự kiểm trên `student_drop/` khi có; thêm kịch bản claim trùng nhau chạy đồng thời trên cùng đơn ở mức shape (hiện mới kiểm ở mức host).

## 8. Tài liệu tham khảo

- Đề bài và docs của lab: `README.md`, `docs/business_rules.md`, `docs/contracts.md`, `docs/metrics.md`, `docs/architecture.md`.
- Google Research, Google DeepMind, MIT. *Towards a Science of Scaling Agent Systems*. arXiv:2512.08296, 2025. https://arxiv.org/abs/2512.08296
- Google Research Blog. *Towards a science of scaling agent systems: When and why agent systems work*, 28/01/2026. https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/
