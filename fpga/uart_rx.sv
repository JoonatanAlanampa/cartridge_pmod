// uart_rx.sv — 8N1 serial receiver. DIV = clocks per bit.
// `valid` pulses one cycle with `data` on a good stop bit; framing
// errors are dropped silently.
`default_nettype none

module uart_rx #(
    parameter DIV = 217
) (
    input  logic       clk, rst,
    input  logic       rx,
    output logic [7:0] data,
    output logic       valid
);
    logic [1:0]  sync;
    always_ff @(posedge clk) sync <= {sync[0], rx};
    wire rxs = sync[1];

    logic [15:0] cnt;
    logic [3:0]  bits;   // 0 = idle, 1..8 data, 9 stop
    logic        run;

    always_ff @(posedge clk)
        if (rst) begin
            run <= 1'b0; valid <= 1'b0; cnt <= '0; bits <= '0;
        end else begin
            valid <= 1'b0;
            if (!run) begin
                if (!rxs) begin              // start edge: sample mid-bit
                    run  <= 1'b1;
                    cnt  <= 16'(DIV + DIV / 2 - 1);
                    bits <= 4'd0;
                end
            end else if (cnt != 16'd0)
                cnt <= cnt - 16'd1;
            else if (bits < 4'd8) begin      // data bits, LSB first
                data <= {rxs, data[7:1]};
                bits <= bits + 4'd1;
                cnt  <= 16'(DIV - 1);
            end else begin                   // stop bit position
                run <= 1'b0;
                if (rxs) valid <= 1'b1;
            end
        end
endmodule
