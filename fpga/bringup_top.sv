// bringup_top.sv — ULX3S bring-up harness for the Cartridge Pmod v0.1.
//
// Plug the cartridge into the ULX3S J1 header END columns, pins 1-12:
// the Pmod's VCC column mates J1 pins 1/2 (3.3V), GND column pins 3/4,
// signal columns land on GP/GN 0-3. Which cartridge row lands on GP vs GN
// depends on mechanical orientation, so the FSM probes both mappings and
// locks the one whose flash JEDEC ID reads back correctly:
//   mapping A: SCK=GP0 MISO=GP1 MOSI=GP2 FCS=GP3 / AUD=GN0 RCS=GN1 SD3=GN2 SD2=GN3
//   mapping B: rows swapped (GP <-> GN)
//
// Test sequence (report on FTDI UART, 115200 8N1, and LEDs):
//   1. flash release-from-power-down (ABh), JEDEC ID (9Fh) == EF 40 18
//   2. PSRAM reset (66h/99h), read ID (9Fh) == 0D 5D
//   3. PSRAM memory test: two 4-byte write/read patterns at distinct
//      addresses + re-read of the first (aliasing check); CS-low bursts
//      kept ~5 us < the APS6404's 8 us tCEM limit
//   4. flash first 4 bytes read (03h) — reported, not judged (blank = FF)
//   5. 440 Hz sigma-delta test tone on the cartridge AUDIO pin
//
// LEDs: 0 heartbeat / 1 flash OK / 2 PSRAM OK / 3 mem OK / 4 mapping B
//       5 done / 6 any-fail / 7 audio enabled.  BTN1 (fire1) re-runs.
`default_nettype none

module bringup_top #(
    parameter int BOOT_CYCLES = 500000,   // 20 ms rail settle
    parameter int UART_DIV    = 217       // 25 MHz / 115200
) (
    input  logic       clk_25mhz,
    input  logic [6:0] btn,        // btn[0] = PWR, pulled up, press = 0
    output logic [7:0] led,
    output logic       ftdi_rxd,   // FPGA -> FTDI -> PC
    inout  wire  [3:0] pmod_gp,    // J1 header GP0-3
    inout  wire  [3:0] pmod_gn,    // J1 header GN0-3
    output logic       wifi_gpio0
);
    assign wifi_gpio0 = 1'b1;      // keep the ESP32 from powering the board off

    // ------------------------------------------------------------- reset ---
    logic [15:0] por = '0;
    wire rst = !btn[0] || !(&por);
    always_ff @(posedge clk_25mhz) if (!(&por)) por <= por + 16'd1;

    // ------------------------------------------------- pin mapping A / B ---
    logic map_b;                   // 0 = mapping A, 1 = mapping B
    logic sck, mosi, fcs_n, rcs_n, audio;
    logic miso;

    // outputs (SD2/SD3 = flash /WP //HOLD: hold high for plain SPI)
    assign pmod_gp[0] = map_b ? audio : sck;
    assign pmod_gp[1] = map_b ? rcs_n : 1'bz;      // A: MISO input
    assign pmod_gp[2] = map_b ? 1'b1  : mosi;      // B: SD3
    assign pmod_gp[3] = map_b ? 1'b1  : fcs_n;     // B: SD2
    assign pmod_gn[0] = map_b ? sck   : audio;
    assign pmod_gn[1] = map_b ? 1'bz  : rcs_n;     // B: MISO input
    assign pmod_gn[2] = map_b ? mosi  : 1'b1;
    assign pmod_gn[3] = map_b ? fcs_n : 1'b1;
    assign miso = map_b ? pmod_gn[1] : pmod_gp[1];

    // --------------------------------------------------------- SPI engine ---
    logic       sp_start, sp_busy, sp_done;
    logic [7:0] sp_tx, sp_rx;
    spi_byte u_spi (
        .clk(clk_25mhz), .rst(rst),
        .start(sp_start), .tx_byte(sp_tx), .rx_byte(sp_rx),
        .busy(sp_busy), .done(sp_done),
        .sck(sck), .mosi(mosi), .miso(miso)
    );

    // ------------------------------------------------- transaction table ---
    // phase -> {flash-not-ram, #cmd bytes, #read bytes, cmd bytes msb-first}
    logic [4:0]  ph;
    logic        t_flash;
    logic [3:0]  t_ncmd, t_nrd;
    logic [63:0] t_cmd;
    always_comb begin
        t_flash = 1'b0; t_ncmd = 4'd1; t_nrd = 4'd0; t_cmd = 64'h0;
        case (ph)
            5'd0:  begin t_flash = 1'b1; t_ncmd = 4'd1; t_cmd = {8'hAB, 56'h0}; end
            5'd1:  begin t_flash = 1'b1; t_ncmd = 4'd1; t_nrd = 4'd3; t_cmd = {8'h9F, 56'h0}; end
            5'd2:  begin t_ncmd = 4'd1; t_cmd = {8'h66, 56'h0}; end
            5'd3:  begin t_ncmd = 4'd1; t_cmd = {8'h99, 56'h0}; end
            5'd4:  begin t_ncmd = 4'd4; t_nrd = 4'd2; t_cmd = {32'h9F000000, 32'h0}; end
            5'd5:  begin t_ncmd = 4'd8; t_cmd = {32'h02000000, 32'hAA55C33C}; end
            5'd6:  begin t_ncmd = 4'd4; t_nrd = 4'd4; t_cmd = {32'h03000000, 32'h0}; end
            5'd7:  begin t_ncmd = 4'd8; t_cmd = {32'h02012344, 32'h5AA50FF0}; end
            5'd8:  begin t_ncmd = 4'd4; t_nrd = 4'd4; t_cmd = {32'h03012344, 32'h0}; end
            5'd9:  begin t_ncmd = 4'd4; t_nrd = 4'd4; t_cmd = {32'h03000000, 32'h0}; end
            5'd10: begin t_flash = 1'b1; t_ncmd = 4'd4; t_nrd = 4'd4; t_cmd = {32'h03000000, 32'h0}; end
            default: ;
        endcase
    end

    // -------------------------------------------------------- results ---
    logic [23:0] fid;
    logic [15:0] pid;
    logic [31:0] fdata, rxbuf;
    logic pass_f, pass_p, m1, m2, m3, tried_b, done_all;
    wire  pass_m = m1 && m2 && m3;

    // ------------------------------------------------------- main FSM ---
    typedef enum logic [2:0] {
        S_BOOT, S_TSTART, S_TCMD, S_TREAD, S_TEND, S_DECIDE, S_REPORT, S_DONE
    } state_t;
    state_t st;

    logic [31:0] wait_cnt;
    logic [3:0]  bidx;
    logic        rep_go;

    always_ff @(posedge clk_25mhz)
        if (rst) begin
            st <= S_BOOT; ph <= 5'd0; map_b <= 1'b0; tried_b <= 1'b0;
            fcs_n <= 1'b1; rcs_n <= 1'b1; sp_start <= 1'b0; rep_go <= 1'b0;
            pass_f <= 1'b0; pass_p <= 1'b0; m1 <= 1'b0; m2 <= 1'b0; m3 <= 1'b0;
            done_all <= 1'b0; wait_cnt <= 32'd0; bidx <= 4'd0;
            fid <= '0; pid <= '0; fdata <= '0; rxbuf <= '0;
        end else begin
            sp_start <= 1'b0;
            rep_go   <= 1'b0;
            case (st)
                S_BOOT: begin
                    wait_cnt <= wait_cnt + 32'd1;
                    if (wait_cnt >= 32'(BOOT_CYCLES)) begin
                        wait_cnt <= 32'd0;
                        st <= S_TSTART;
                    end
                end
                S_TSTART: begin                       // assert CS, arm byte 0
                    if (t_flash) fcs_n <= 1'b0; else rcs_n <= 1'b0;
                    bidx <= 4'd0;
                    st <= S_TCMD;
                    sp_start <= 1'b1;
                    sp_tx <= t_cmd[63 -: 8];
                end
                S_TCMD: begin
                    if (sp_done) begin
                        if (bidx == t_ncmd - 4'd1) begin
                            bidx <= 4'd0;
                            if (t_nrd != 4'd0) begin
                                st <= S_TREAD;
                                sp_start <= 1'b1;
                                sp_tx <= 8'h00;
                            end else
                                st <= S_TEND;
                        end else begin
                            bidx <= bidx + 4'd1;
                            sp_start <= 1'b1;
                            sp_tx <= t_cmd[8*(4'd6 - bidx) +: 8]; // next cmd byte
                        end
                    end
                end
                S_TREAD: begin
                    if (sp_done) begin
                        rxbuf <= {rxbuf[23:0], sp_rx};
                        if (bidx == t_nrd - 4'd1) begin
                            bidx <= 4'd0;
                            st <= S_TEND;
                        end else begin
                            bidx <= bidx + 4'd1;
                            sp_start <= 1'b1;
                            sp_tx <= 8'h00;
                        end
                    end
                end
                S_TEND: begin                          // raise CS, settle
                    fcs_n <= 1'b1; rcs_n <= 1'b1;
                    wait_cnt <= wait_cnt + 32'd1;
                    if (wait_cnt >= 32'd128) begin     // >= 5 us gap / tRES1
                        wait_cnt <= 32'd0;
                        st <= S_DECIDE;
                    end
                end
                S_DECIDE: begin
                    st <= S_TSTART;                    // default: next phase
                    ph <= ph + 5'd1;
                    case (ph)
                        5'd1: begin
                            fid    <= rxbuf[23:0];
                            pass_f <= (rxbuf[23:0] == 24'hEF4018);
                            if (rxbuf[23:0] != 24'hEF4018 && !tried_b) begin
                                map_b <= !map_b;       // flip rows, retry
                                tried_b <= 1'b1;
                                ph <= 5'd0;
                            end
                        end
                        5'd4: begin
                            pid    <= rxbuf[15:0];
                            pass_p <= (rxbuf[15:0] == 16'h0D5D);
                        end
                        5'd6: m1 <= (rxbuf == 32'hAA55C33C);
                        5'd8: m2 <= (rxbuf == 32'h5AA50FF0);
                        5'd9: m3 <= (rxbuf == 32'hAA55C33C);
                        5'd10: begin
                            fdata <= rxbuf;
                            rep_go <= 1'b1;
                            st <= S_REPORT;
                        end
                        default: ;
                    endcase
                end
                S_REPORT: if (rep_done) begin
                    done_all <= 1'b1;
                    st <= S_DONE;
                end
                S_DONE: begin                          // BTN1 re-runs everything
                    if (btn[1]) begin
                        ph <= 5'd0; map_b <= 1'b0; tried_b <= 1'b0;
                        pass_f <= 1'b0; pass_p <= 1'b0;
                        m1 <= 1'b0; m2 <= 1'b0; m3 <= 1'b0;
                        done_all <= 1'b0;
                        st <= S_BOOT;
                    end
                end
                default: st <= S_BOOT;
            endcase
        end

    // ------------------------------------------------------ UART report ---
    localparam [8*22-1:0] T_TITLE = "CARTRIDGE-PMOD BRINGUP";
    localparam [8*4 -1:0] T_MAP   = "MAP ";
    localparam [8*6 -1:0] T_FLASH = "FLASH ";
    localparam [8*6 -1:0] T_PSRAM = "PSRAM ";
    localparam [8*3 -1:0] T_MEM   = "MEM";
    localparam [8*8 -1:0] T_FRD   = "FLASH@0 ";
    localparam [8*4 -1:0] T_DONE  = "DONE";
    localparam [8*5 -1:0] T_PASS  = " PASS";
    localparam [8*5 -1:0] T_FAIL  = " FAIL";

    // print program: {item type, length}; types: 0 NL, 1..7 literals,
    // 8 map char, 9 hex(fid,6), 10 hex(pid,4), 11 hex(fdata,8), 12..14 P/F
    logic [4:0] r_item;
    logic [4:0] r_ch;
    logic [3:0] it_len;
    always_comb
        case (r_item)
            5'd0, 5'd2, 5'd5, 5'd9, 5'd13, 5'd16, 5'd19, 5'd21: it_len = 4'd2;  // NL
            5'd1:  it_len = 4'd11; // title part 1 (11+11 chars, split below)
            5'd22: it_len = 4'd11; // (unused tail guard)
            5'd3:  it_len = 4'd4;  // "MAP "
            5'd4:  it_len = 4'd1;  // A/B/!
            5'd6:  it_len = 4'd6;  // "FLASH "
            5'd7:  it_len = 4'd6;  // fid hex
            5'd8:  it_len = 4'd5;  // pass/fail
            5'd10: it_len = 4'd6;  // "PSRAM "
            5'd11: it_len = 4'd4;  // pid hex
            5'd12: it_len = 4'd5;
            5'd14: it_len = 4'd3;  // "MEM"
            5'd15: it_len = 4'd5;
            5'd17: it_len = 4'd8;  // "FLASH@0 "
            5'd18: it_len = 4'd8;  // fdata hex
            5'd20: it_len = 4'd4;  // "DONE"
            default: it_len = 4'd1;
        endcase

    // title is 22 chars > one 4-bit length: emit as two 11-char halves
    function automatic [7:0] hexch(input [3:0] n);
        hexch = (n < 4'd10) ? (8'h30 + 8'(n)) : (8'h37 + 8'(n));
    endfunction

    logic [7:0] r_char;
    always_comb begin
        r_char = 8'h3F; // '?'
        case (r_item)
            5'd0, 5'd2, 5'd5, 5'd9, 5'd13, 5'd16, 5'd19, 5'd21:
                r_char = (r_ch == 5'd0) ? 8'h0D : 8'h0A;
            5'd1:  r_char = T_TITLE[8*(21 - r_ch) +: 8];        // chars 0-10
            5'd22: r_char = T_TITLE[8*(10 - r_ch) +: 8];        // chars 11-21
            5'd3:  r_char = T_MAP  [8*(3  - r_ch) +: 8];
            5'd4:  r_char = pass_f ? (map_b ? 8'h42 : 8'h41) : 8'h21; // B/A/!
            5'd6:  r_char = T_FLASH[8*(5  - r_ch) +: 8];
            5'd7:  r_char = hexch(fid  [4*(5 - r_ch) +: 4]);
            5'd8:  r_char = pass_f ? T_PASS[8*(4 - r_ch) +: 8]
                                   : T_FAIL[8*(4 - r_ch) +: 8];
            5'd10: r_char = T_PSRAM[8*(5  - r_ch) +: 8];
            5'd11: r_char = hexch(pid  [4*(3 - r_ch) +: 4]);
            5'd12: r_char = pass_p ? T_PASS[8*(4 - r_ch) +: 8]
                                   : T_FAIL[8*(4 - r_ch) +: 8];
            5'd14: r_char = T_MEM  [8*(2  - r_ch) +: 8];
            5'd15: r_char = pass_m ? T_PASS[8*(4 - r_ch) +: 8]
                                   : T_FAIL[8*(4 - r_ch) +: 8];
            5'd17: r_char = T_FRD  [8*(7  - r_ch) +: 8];
            5'd18: r_char = hexch(fdata[4*(7 - r_ch) +: 4]);
            5'd20: r_char = T_DONE [8*(3  - r_ch) +: 8];
            default: ;
        endcase
    end

    // item order with the split title: 0 NL, 1 title[0:10], 22 title[11:21],
    // 2 NL, 3 "MAP ", 4 ch, 5 NL, ... 21 NL, then stop (23).
    function automatic [4:0] next_item(input [4:0] it);
        case (it)
            5'd1:    next_item = 5'd22;
            5'd22:   next_item = 5'd2;
            5'd21:   next_item = 5'd23;   // end
            default: next_item = it + 5'd1;
        endcase
    endfunction

    logic       u_wr;
    logic [7:0] u_data;
    logic       u_busy;
    logic       rep_done, printing;

    always_ff @(posedge clk_25mhz)
        if (rst) begin
            printing <= 1'b0; rep_done <= 1'b0; u_wr <= 1'b0;
            r_item <= 5'd0; r_ch <= 5'd0;
        end else begin
            u_wr <= 1'b0;
            rep_done <= 1'b0;
            if (!printing) begin
                if (rep_go) begin
                    printing <= 1'b1;
                    r_item <= 5'd0; r_ch <= 5'd0;
                end
            end else if (!u_busy && !u_wr) begin
                u_wr   <= 1'b1;
                u_data <= r_char;
                if (r_ch == 5'(it_len) - 5'd1) begin
                    r_ch <= 5'd0;
                    if (next_item(r_item) == 5'd23) begin
                        printing <= 1'b0;
                        rep_done <= 1'b1;
                    end else
                        r_item <= next_item(r_item);
                end else
                    r_ch <= r_ch + 5'd1;
            end
        end

    uart_tx #(.DIV(UART_DIV)) u_uart (
        .clk(clk_25mhz), .rst(rst),
        .wr(u_wr), .data(u_data),
        .tx(ftdi_rxd), .busy(u_busy)
    );

    // ------------------------------------------------- 440 Hz test tone ---
    // quarter-wave-symmetric 32-entry sine, 8-bit unsigned
    localparam [8*32-1:0] SINL = {
        8'd128, 8'd152, 8'd176, 8'd198, 8'd218, 8'd234, 8'd245, 8'd253,
        8'd255, 8'd253, 8'd245, 8'd234, 8'd218, 8'd198, 8'd176, 8'd152,
        8'd128, 8'd103, 8'd79,  8'd57,  8'd37,  8'd21,  8'd10,  8'd2,
        8'd0,   8'd2,   8'd10,  8'd21,  8'd37,  8'd57,  8'd79,  8'd103 };
    logic [31:0] ph_acc;
    logic [8:0]  sd_acc;
    wire  [7:0]  samp = SINL[8*(31 - ph_acc[31:27]) +: 8];
    wire         audio_en = done_all && pass_f;
    always_ff @(posedge clk_25mhz)
        if (rst) begin
            ph_acc <= '0; sd_acc <= '0; audio <= 1'b0;
        end else begin
            ph_acc <= ph_acc + 32'd75573;            // 440 Hz @ 25 MHz
            sd_acc <= {1'b0, sd_acc[7:0]} + {1'b0, samp};
            audio  <= audio_en && sd_acc[8];         // 1st-order sigma-delta
        end

    // --------------------------------------------------------------- LEDs ---
    logic [23:0] hb = '0;
    always_ff @(posedge clk_25mhz) hb <= hb + 24'd1;
    assign led = {audio_en, !pass_f || !pass_p || !pass_m, done_all, map_b,
                  pass_m, pass_p, pass_f, hb[23]};
endmodule
