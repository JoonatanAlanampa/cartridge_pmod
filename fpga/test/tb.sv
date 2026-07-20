// tb.sv — testbench harness: bringup_top + behavioral W25Q128 / APS6404
// models wired like the cartridge Pmod. Plusarg +MAPB=1 mates the cartridge
// in the flipped row orientation (GP<->GN), exercising the autodetect.
`timescale 1ns/1ps
`default_nettype none

// ---------------------------------------------------------------------------
// minimal SPI-mode-0 slave: W25Q128 flash (9F ID, AB wake, 03 read)
module flash_model (
    input  wire cs_n, sck, si,
    output wire so_oe, so_val
);
    logic [7:0]  cmd;
    logic [3:0]  bitcnt;
    logic [31:0] bytecnt;
    logic [23:0] addr;
    logic [7:0]  shin, shout;
    logic        out_en;
    logic [7:0]  mem [0:255];
    initial for (int i = 0; i < 256; i++) mem[i] = 8'hFF;
    initial begin mem[0]=8'hDE; mem[1]=8'hAD; mem[2]=8'hBE; mem[3]=8'hEF; end

    assign so_oe  = !cs_n && out_en;
    assign so_val = shout[7];

    always @(negedge cs_n) begin
        bitcnt = 0; bytecnt = 0; cmd = 0; out_en = 0;
    end

    always @(posedge sck) if (!cs_n) begin
        shin = {shin[6:0], si};
        bitcnt = bitcnt + 1;
        if (bitcnt == 8) begin
            bitcnt = 0;
            bytecnt = bytecnt + 1;
            if (bytecnt == 1) cmd = shin;
            else if (cmd == 8'h03 && bytecnt <= 4)
                addr = {addr[15:0], shin};
        end
    end

    always @(negedge sck) if (!cs_n) begin
        if (bitcnt == 0) begin      // byte boundary: load next output byte
            case (cmd)
                8'h9F: begin
                    out_en = (bytecnt >= 1);
                    case (bytecnt)
                        1: shout = 8'hEF;
                        2: shout = 8'h40;
                        3: shout = 8'h18;
                        default: shout = 8'h00;
                    endcase
                end
                8'h03: begin
                    out_en = (bytecnt >= 4);
                    if (bytecnt >= 4) begin
                        shout = mem[addr[7:0]];
                        addr  = addr + 1;
                    end
                end
                default: out_en = 0;
            endcase
        end else if (out_en)
            shout = {shout[6:0], 1'b0};
    end
endmodule

// ---------------------------------------------------------------------------
// minimal APS6404 PSRAM (66/99 reset, 9F+3addr ID, 03 read, 02 write)
// asserts tCEM: CS low must stay under 8 us
module psram_model (
    input  wire cs_n, sck, si,
    output wire so_oe, so_val
);
    logic [7:0]  cmd;
    logic [3:0]  bitcnt;
    logic [31:0] bytecnt;
    logic [23:0] addr;
    logic [7:0]  shin, shout;
    logic        out_en;
    logic [7:0]  mem [0:(1<<17)-1];   // 128 KB window is plenty for the test
    realtime     cs_fall;

    assign so_oe  = !cs_n && out_en;
    assign so_val = shout[7];

    always @(negedge cs_n) begin
        bitcnt = 0; bytecnt = 0; cmd = 0; out_en = 0;
        cs_fall = $realtime;
    end
    always @(posedge cs_n)
        if ($realtime - cs_fall > 8000.0)
            $fatal(1, "psram_model: tCEM violated, CS low %.1f ns", $realtime - cs_fall);

    always @(posedge sck) if (!cs_n) begin
        shin = {shin[6:0], si};
        bitcnt = bitcnt + 1;
        if (bitcnt == 8) begin
            bitcnt = 0;
            bytecnt = bytecnt + 1;
            if (bytecnt == 1) cmd = shin;
            else if ((cmd == 8'h03 || cmd == 8'h02 || cmd == 8'h9F) && bytecnt <= 4)
                addr = {addr[15:0], shin};
            else if (cmd == 8'h02 && bytecnt > 4) begin
                mem[addr[16:0]] = shin;
                addr = addr + 1;
            end
        end
    end

    always @(negedge sck) if (!cs_n) begin
        if (bitcnt == 0) begin
            case (cmd)
                8'h9F: begin
                    out_en = (bytecnt >= 4);
                    case (bytecnt)
                        4: shout = 8'h0D;        // MF ID
                        5: shout = 8'h5D;        // KGD
                        default: shout = 8'h55;  // EID filler
                    endcase
                end
                8'h03: begin
                    out_en = (bytecnt >= 4);
                    if (bytecnt >= 4) begin
                        shout = mem[addr[16:0]];
                        addr  = addr + 1;
                    end
                end
                default: out_en = 0;
            endcase
        end else if (out_en)
            shout = {shout[6:0], 1'b0};
    end
endmodule

// ---------------------------------------------------------------------------
module tb;
    logic clk = 0;
    always #20 clk = ~clk;    // 25 MHz

    logic [6:0] btn = 7'b0000001;   // btn[0] high = not pressed
    wire  [7:0] led;
    wire        ftdi_rxd, wifi_gpio0;
    tri1  [3:0] gp, gn;             // header pullups (LPF PULLMODE=UP)

    bringup_top #(.BOOT_CYCLES(64)) dut (
        .clk_25mhz(clk), .btn(btn), .led(led),
        .ftdi_rxd(ftdi_rxd),
        .pmod_gp(gp), .pmod_gn(gn),
        .wifi_gpio0(wifi_gpio0)
    );

    // cartridge orientation: MAPB=0 -> row 1-6 on GP (mapping A);
    // MAPB=1 -> rows swapped
    integer mapb = 0;
    initial begin
        if (!$value$plusargs("MAPB=%d", mapb)) mapb = 0;
    end

    // cartridge signal lines as seen by the chips
    wire l_sck  = mapb ? gn[0] : gp[0];
    wire l_miso;                             // chips drive this line
    wire l_mosi = mapb ? gn[2] : gp[2];
    wire l_fcs  = mapb ? gn[3] : gp[3];
    wire l_rcs  = mapb ? gp[1] : gn[1];
    wire l_aud  = mapb ? gp[0] : gn[0];

    wire f_oe, f_val, p_oe, p_val;
    assign l_miso = f_oe ? f_val : (p_oe ? p_val : 1'bz);
    assign gp[1] = (mapb == 0 && f_oe) ? f_val :
                   (mapb == 0 && p_oe) ? p_val : 1'bz;
    assign gn[1] = (mapb != 0 && f_oe) ? f_val :
                   (mapb != 0 && p_oe) ? p_val : 1'bz;

    flash_model u_flash (.cs_n(l_fcs), .sck(l_sck), .si(l_mosi),
                         .so_oe(f_oe), .so_val(f_val));
    psram_model u_psram (.cs_n(l_rcs), .sck(l_sck), .si(l_mosi),
                         .so_oe(p_oe), .so_val(p_val));

    initial begin
        if ($test$plusargs("VCD")) begin
            $dumpfile("tb.vcd");
            $dumpvars(0, tb);
        end
    end
endmodule
