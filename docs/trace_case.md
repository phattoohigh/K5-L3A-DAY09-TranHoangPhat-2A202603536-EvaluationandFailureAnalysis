# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Case đã phân tích

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-014@11`; run ID được sinh bởi harness khi chạy report M4 |
| Triệu chứng | Lab 8 grader fail `proposal_mismatch`; reply nói 120.000đ nhưng ledger chỉ ghi 90.000đ, label yêu cầu 120.000đ. |
| Bước sai đầu tiên | Event 5 `proposal {"amount_vnd": 120000}`: agent tự trừ 30.000đ lịch sử khỏi quote 150.000đ trước khi gọi host. |
| Vì sao là bước *đầu tiên* | Event 1 handoff đúng scope; event 2 đọc đúng order; event 3 quote đúng entitlement 150.000đ; event 4 đọc đúng lịch sử đã hoàn 30.000đ. Sai lệch chỉ bắt đầu khi agent tự trừ ở event 5. |
| Failure mode | FM-05 `pre_deducted`. |
| Đối chứng | `fixed C-014@11` không có event `refund_history`/`proposal`; nó gửi quote đầy đủ 150.000đ cho host và host commit đúng phần chênh 120.000đ. |
| Regression test | `test_pre_deducted_trace_case_regression` replay đúng C-014@11, khẳng định `seeded_regression` ghi 90.000đ và bị `RefundAmountCorrect` bắt, trong khi `fixed` ghi đúng 120.000đ và pass. |
| Chưa chắc chắn | Trace chứng minh double deduction và ledger sai, nhưng không tự chứng minh intent của model; kết luận chỉ dựa trên event và state quan sát được. |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
