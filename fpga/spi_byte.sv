// spi_byte.sv — byte-level SPI master, mode 0, SCK = clk/2.
// Pulse `start` with `tx_byte` while !busy; `done` pulses for 1 cycle with
// `rx_byte` valid. MOSI changes on the SCK low half, MISO is sampled on the
// rising edge. CS is managed by the caller; SCK idles low.
`default_nettype none

module spi_byte (
    input  logic       clk, rst,
    input  logic       start,
    input  logic [7:0] tx_byte,
    output logic [7:0] rx_byte,
    output logic       busy,
    output logic       done,
    output logic       sck,
    output logic       mosi,
    input  logic       miso
);
    logic [7:0] sh;
    logic [3:0] bits;   // bits remaining
    logic       phase;  // 0: low half (mosi set), 1: high half (sample)

    always_ff @(posedge clk)
        if (rst) begin
            busy <= 1'b0; done <= 1'b0; sck <= 1'b0;
            mosi <= 1'b0; bits <= 4'd0; phase <= 1'b0;
        end else begin
            done <= 1'b0;
            if (!busy) begin
                if (start) begin
                    sh    <= tx_byte;
                    bits  <= 4'd8;
                    phase <= 1'b0;
                    busy  <= 1'b1;
                end
            end else if (!phase) begin       // drive MOSI, SCK low
                mosi  <= sh[7];
                sck   <= 1'b0;
                phase <= 1'b1;
            end else begin                   // SCK high, sample MISO
                sck     <= 1'b1;
                rx_byte <= {rx_byte[6:0], miso};
                sh      <= {sh[6:0], 1'b0};
                bits    <= bits - 4'd1;
                phase   <= 1'b0;
                if (bits == 4'd1) begin
                    busy <= 1'b0;
                    done <= 1'b1;
                end
            end
            if (!busy && !start) sck <= 1'b0;   // idle low between bytes
        end
endmodule
