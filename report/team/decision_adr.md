# Decision record

Điền sau dấu `:` trên cùng dòng, không xóa nhãn. Giảng viên và `python -m lab8.check_submission` (chạy trong `src/`) đọc các dòng này bằng máy. Không đổi tên hay dời file này khỏi `report/team/`.
`Shape chọn` phải là đúng một trong: `workflow`, `single`, `orchestrator`, `swarm`. Đây là shape được chấm cổng hidden.

- Shape chọn: workflow
- Commit hash:
- Run id dẫn chứng: R-workflow-C-002-s55, R-workflow-C-014-s55, R-workflow-C-007-s11 (trials trong src/reports/benchmark.json); đối chứng R-swarm-C-002-s55 (fail)
- Pass rate / pass^5 / seed min-max / variance: 1.000 / 1.000 / 1.000–1.000 / 0.000000 (src/reports/benchmark.json, 14 claim public × seed 11,22,33,44,55 = 70 trial)
- Cost per success (mô phỏng, VND): 28.79 (workflow) so với single 29.28, swarm 49.57, orchestrator 57.19
- Crash safety: 20/20 (src/reports/crash.json); T12 của workflow xanh trong ma trận student
- Secret leak / approval bypass: 0 / 0 trên public: 70/70 trial workflow pass, không trial nào có `forbidden_substring`, T07 (approval hết hạn) và T13 (đơn đã hoàn) không ghi ledger. Số chính thức của hidden do grader giảng viên tính

Ví dụ một dòng đã điền: `- Shape chọn: workflow`, `- Crash safety: 20/20 (src/reports/crash.json)`.

## Vì sao shape này

Trên cùng 14 claim public, cùng 5 seed, cùng MockLLM và cùng bảng giá (`src/reports/benchmark.json`), ba shape nhóm viết đều đạt pass rate 1.000, pass^5 1.000, variance 0. Swarm đạt 0.986 / 0.929 vì fail T02 ở seed 55 (tin số ngày trong ticket). Khi pass như nhau, nhóm chọn shape **ít tự chủ nhất**: workflow. Workflow có cost/success thấp nhất (28.79 VND, bằng khoảng một nửa orchestrator 57.19), chỉ một model call mỗi trial (soạn câu trả lời) và không để model chạm vào số tiền hay thứ tự bước. Nhóm còn chạy thêm 13 kịch bản giống bộ hidden × 5 seed (65 trial) cho mỗi shape (`src/tests/test_shapes_adversarial.py`: ticket nói dối, injection, approval mượn/thu hồi/thiếu, đơn hủy/đang giao, homoglyph, principal lẫn, cộng dồn ship + hỏng hàng). Cả ba shape đều qua hết; cùng bộ đó bắt được swarm fail ở `C-ADV-LIE` seed 55.

## Có đáng đổi lấy multi-agent không

Không, ít nhất là trên dữ liệu hiện có. Orchestrator không pass cao hơn workflow nhưng tốn gấp khoảng 2 lần cost/success (57.19 so với 28.79) và gấp khoảng 2 lần tool call (5.57 so với 2.79 mỗi trial). Swarm vừa đắt hơn (49.57) vừa có variance khác 0. Task claim ở đây là chuỗi tuần tự ngắn (đọc claim → đọc đơn → tính quote → gọi host), mọi dữ kiện đã có cấu trúc trong DB, nên lớp agent thêm vào chỉ thêm chi phí phối hợp. Quyết định sẽ đảo lại nếu: (1) ticket thật sự mơ hồ và cần model hiểu ngôn ngữ để chọn bước tiếp theo (khi đó single ReAct hợp hơn); (2) cần gọi nhiều nguồn độc lập chạy song song (nhiều hãng vận chuyển, nhiều hệ thống) mà một workflow cố định phải viết lại liên tục; (3) bộ hidden lộ ra trường hợp workflow cứng không xử lý được mà shape có model lại pass ổn định trên cả 5 seed.

## Trace và bằng chứng

Trace của workflow ghi các event: `claim` (`claim_id`, `has_order_id`), `lookup_order` (`visible`, `reason`), `quote` (`amount_vnd`, `reason`, `clause_ids`), `decision` (status sớm), `issue_refund` (`ok`, `reason`), `crash` (`at`, trước khi ném lại `InjectedCrash`), và `error` (`unknown_claim`). Cố ý **không** ghi: nội dung ticket (dữ liệu người dùng, có thể chứa secret hoặc lệnh injection), `parent_secret`, `raw_headers`, và toàn bộ order row, kể cả các field đã qua allowlist. Chỉ ghi `visible` và `reason`, vì SĐT, địa chỉ, `internal_note`, tên hàng không bao giờ được vào trace. Mọi nhánh return đều đi qua `finish()` nên luôn có trace đúng contract v1. Test `test_no_secret_or_pii_in_any_public_trace` quét kết quả và mọi file `<run_id>*` của 14 claim public trên cả ba shape, tìm mọi chuỗi `CANARY_`, `Bearer ` và PII của mọi đơn trong world, không chỉ chuỗi cấm của nhãn. Nếu trace nằm ngoài chỗ scanner quét được thì không chứng minh được hệ thống không lộ secret. Vì vậy nhóm giữ trace trong `traces/<run_id>.json` và không ghi gì ra stdout hay file khác.

## Giới hạn

MockLLM không phải model sản xuất: hành vi cố định theo seed, nên variance 0 của workflow chỉ nói rằng workflow không phụ thuộc model, không nói gì về một LLM thật. Cost là giá mô phỏng trong `config/pricing.yaml`, không phải hóa đơn API. Latency để `unavailable`. Kết luận dựa trên 14 claim public và 13 kịch bản nhóm tự dựng; pass rate trên 40 claim hidden do grader giảng viên chấm, nhóm chưa có số đó. Không sửa JSON cho đủ 0.75.
