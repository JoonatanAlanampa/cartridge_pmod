// bringup_top.sv — ULX3S bring-up + flash-writer for the Cartridge Pmod v0.1.
//
// Plug the cartridge into the ULX3S J1 header END columns, pins 1-12:
// the Pmod's VCC column mates J1 pins 1/2 (3.3V), GND column pins 3/4,
// signal columns land on GP/GN 0-3. Which cartridge row lands on GP vs GN
// depends on mechanical orientation, so the FSM probes both mappings and
// locks the one whose flash JEDEC ID reads back correctly:
//   mapping A: SCK=GP0 MISO=GP1 MOSI=GP2 FCS=GP3 / AUD=GN0 RCS=GN1 SD3=GN2 SD2=GN3
//   mapping B: rows swapped (GP <-> GN)
//
// Power-up test sequence (report on FTDI UART, 115200 8N1, and LEDs):
//   1. flash release-from-power-down (ABh), JEDEC ID (9Fh) == EF 40 18
//   2. PSRAM reset (66h/99h), read ID (9Fh) == 0D 5D
//   3. PSRAM memory test: two 4-byte write/read patterns at distinct
//      addresses + re-read of the first (aliasing check); CS-low bursts
//      kept ~5 us < the APS6404's 8 us tCEM limit
//   4. flash first 4 bytes read (03h) — reported, not judged (blank = FF)
//   5. 440 Hz sigma-delta test tone on the cartridge AUDIO pin
//
// After DONE the UART becomes a binary flash-writer console (driven by
// fpga/flash_cartridge.py; all multi-byte fields MSB first):
//   'I'                  -> 3 reply bytes: flash JEDEC ID
//   'E' a2 a1 a0         -> 4 KB sector erase @addr, replies 'K' when done
//   'P' a2 a1 a0 + 256B  -> page program @addr (page-aligned), replies 'K'
//   'R' a2 a1 a0         -> replies 256 bytes read from @addr
// WREN and SR1 busy-polling are handled internally.
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
    input  logic       ftdi_txd,   // PC -> FTDI -> FPGA (flash-writer cmds)
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
    // ph 0-10: power-up tests; ph 16-21: flash-writer ops (dynamic fields)
    logic [4:0]  ph;
    logic [23:0] faddr;
    logic [7:0]  fcmd;             // 'E' / 'P' / 'R'
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
            // flash-writer ops (always flash CS)
            5'd16: begin t_flash = 1'b1; t_ncmd = 4'd1; t_cmd = {8'h06, 56'h0}; end
            5'd17: begin t_flash = 1'b1; t_ncmd = 4'd4; t_cmd = {8'h20, faddr, 32'h0}; end
            5'd18: begin t_flash = 1'b1; t_ncmd = 4'd4; t_cmd = {8'h02, faddr, 32'h0}; end // + 256B bulk
            5'd19: begin t_flash = 1'b1; t_ncmd = 4'd1; t_nrd = 4'd1; t_cmd = {8'h05, 56'h0}; end
            5'd20: begin t_flash = 1'b1; t_ncmd = 4'd4; t_cmd = {8'h03, faddr, 32'h0}; end // + 256B stream
            5'd21: begin t_flash = 1'b1; t_ncmd = 4'd1; t_nrd = 4'd3; t_cmd = {8'h9F, 56'h0}; end
            default: ;
        endcase
    end

    // -------------------------------------------------------- results ---
    logic [23:0] fid;
    logic [15:0] pid;
    logic [31:0] fdata, rxbuf;
    logic pass_f, pass_p, m1, m2, m3, tried_b, done_all;
    wire  pass_m = m1 && m2 && m3;

    // ------------------------------------------------------ UART rx/tx ---
    logic [7:0] rx_data;
    logic       rx_valid;
    uart_rx #(.DIV(UART_DIV)) u_urx (
        .clk(clk_25mhz), .rst(rst),
        .rx(ftdi_txd), .data(rx_data), .valid(rx_valid)
    );

    logic       u_busy;
    logic       f_wr;                    // flasher TX path
    logic [7:0] f_data;

    // ------------------------------------------------------- main FSM ---
    typedef enum logic [3:0] {
        S_BOOT, S_TSTART, S_TCMD, S_TREAD, S_TEND, S_DECIDE, S_REPORT, S_DONE,
        S_FRX, S_TBULK, S_TRDS, S_FREPLY
    } state_t;
    state_t st;

    logic [31:0] wait_cnt;
    logic [3:0]  bidx;
    logic        rep_go;
    logic [8:0]  fcnt;                   // bulk byte counter (0..255)
    logic        f_hdr;                  // S_FRX: still collecting address
    logic        frd_pend;               // S_TRDS: byte read, waiting on UART
    logic [23:0] f_shift;                // reply bytes, MSB first
    logic [1:0]  f_rlen;
    logic [7:0]  fbuf [0:255];           // page buffer

    always_ff @(posedge clk_25mhz)
        if (rst) begin
            st <= S_BOOT; ph <= 5'd0; map_b <= 1'b0; tried_b <= 1'b0;
            fcs_n <= 1'b1; rcs_n <= 1'b1; sp_start <= 1'b0; rep_go <= 1'b0;
            pass_f <= 1'b0; pass_p <= 1'b0; m1 <= 1'b0; m2 <= 1'b0; m3 <= 1'b0;
            done_all <= 1'b0; wait_cnt <= 32'd0; bidx <= 4'd0;
            fid <= '0; pid <= '0; fdata <= '0; rxbuf <= '0;
            f_wr <= 1'b0; f_data <= '0; fcnt <= '0; f_hdr <= 1'b0;
            frd_pend <= 1'b0; f_shift <= '0; f_rlen <= '0;
            faddr <= '0; fcmd <= '0;
        end else begin
            sp_start <= 1'b0;
            rep_go   <= 1'b0;
            f_wr     <= 1'b0;
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
                            fcnt <= 9'd0;
                            if (ph == 5'd18) begin        // page program: bulk data
                                st <= S_TBULK;
                                sp_start <= 1'b1;
                                sp_tx <= fbuf[0];
                            end else if (ph == 5'd20) begin // read: stream to UART
                                st <= S_TRDS;
                                frd_pend <= 1'b0;
                                sp_start <= 1'b1;
                                sp_tx <= 8'h00;
                            end else if (t_nrd != 4'd0) begin
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
                S_TBULK: begin                         // 256 data bytes from fbuf
                    if (sp_done) begin
                        if (fcnt == 9'd255)
                            st <= S_TEND;
                        else begin
                            fcnt <= fcnt + 9'd1;
                            sp_start <= 1'b1;
                            sp_tx <= fbuf[fcnt[7:0] + 8'd1];
                        end
                    end
                end
                S_TRDS: begin                          // 256 bytes flash -> UART
                    if (!frd_pend) begin
                        if (sp_done) begin
                            f_data <= sp_rx;
                            frd_pend <= 1'b1;
                        end
                    end else if (!u_busy && !f_wr) begin
                        f_wr <= 1'b1;
                        frd_pend <= 1'b0;
                        if (fcnt == 9'd255)
                            st <= S_TEND;
                        else begin
                            fcnt <= fcnt + 9'd1;
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
                        // ---- flash-writer op routing ----
                        5'd16: begin                   // WREN done
                            ph <= (fcmd == 8'h45) ? 5'd17 : 5'd18; // 'E' / 'P'
                        end
                        5'd17, 5'd18: ph <= 5'd19;     // erase/program -> poll
                        5'd19: begin                   // SR1 in rxbuf[7:0]
                            if (rxbuf[0])
                                ph <= 5'd19;           // still busy: re-poll
                            else begin
                                f_shift <= {8'h4B, 16'h0};  // 'K'
                                f_rlen  <= 2'd1;
                                st <= S_FREPLY;
                            end
                        end
                        5'd20: st <= S_DONE;           // bytes already streamed
                        5'd21: begin                   // ID reply
                            f_shift <= rxbuf[23:0];
                            f_rlen  <= 2'd3;
                            st <= S_FREPLY;
                        end
                        default: ;
                    endcase
                end
                S_REPORT: if (rep_done) begin
                    done_all <= 1'b1;
                    st <= S_DONE;
                end
                S_DONE: begin                          // dispatch; BTN1 re-runs
                    if (btn[1]) begin
                        ph <= 5'd0; map_b <= 1'b0; tried_b <= 1'b0;
                        pass_f <= 1'b0; pass_p <= 1'b0;
                        m1 <= 1'b0; m2 <= 1'b0; m3 <= 1'b0;
                        done_all <= 1'b0;
                        st <= S_BOOT;
                    end else if (rx_valid) begin
                        fcmd <= rx_data;
                        case (rx_data)
                            8'h49: begin ph <= 5'd21; st <= S_TSTART; end   // 'I'
                            8'h45, 8'h50, 8'h52: begin                      // E/P/R
                                fcnt <= 9'd0;
                                f_hdr <= 1'b1;
                                st <= S_FRX;
                            end
                            default: ;                 // ignore strays
                        endcase
                    end
                end
                S_FRX: begin                           // addr (3B) [+ 256B data]
                    if (rx_valid) begin
                        if (f_hdr) begin
                            faddr <= {faddr[15:0], rx_data};
                            if (fcnt == 9'd2) begin
                                fcnt <= 9'd0;
                                f_hdr <= 1'b0;
                                if (fcmd == 8'h50)      // 'P': collect page
                                    ;
                                else begin
                                    ph <= (fcmd == 8'h45) ? 5'd16 : 5'd20;
                                    st <= S_TSTART;
                                end
                            end else
                                fcnt <= fcnt + 9'd1;
                        end else begin
                            fbuf[fcnt[7:0]] <= rx_data;
                            if (fcnt == 9'd255) begin
                                fcnt <= 9'd0;
                                ph <= 5'd16;            // WREN, then program
                                st <= S_TSTART;
                            end else
                                fcnt <= fcnt + 9'd1;
                        end
                    end
                end
                S_FREPLY: begin
                    if (f_rlen == 2'd0)
                        st <= S_DONE;
                    else if (!u_busy && !f_wr) begin
                        f_wr <= 1'b1;
                        f_data <= f_shift[23:16];
                        f_shift <= {f_shift[15:0], 8'h0};
                        f_rlen <= f_rlen - 2'd1;
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

    logic [4:0] r_item;
    logic [4:0] r_ch;
    logic [3:0] it_len;
    always_comb
        case (r_item)
            5'd0, 5'd2, 5'd5, 5'd9, 5'd13, 5'd16, 5'd19, 5'd21: it_len = 4'd2;  // NL
            5'd1:  it_len = 4'd11; // title, first half
            5'd22: it_len = 4'd11; // title, second half
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

    function automatic [4:0] next_item(input [4:0] it);
        case (it)
            5'd1:    next_item = 5'd22;
            5'd22:   next_item = 5'd2;
            5'd21:   next_item = 5'd23;   // end
            default: next_item = it + 5'd1;
        endcase
    endfunction

    logic       p_wr;
    logic [7:0] p_data;
    logic       rep_done, printing;

    always_ff @(posedge clk_25mhz)
        if (rst) begin
            printing <= 1'b0; rep_done <= 1'b0; p_wr <= 1'b0;
            r_item <= 5'd0; r_ch <= 5'd0;
        end else begin
            p_wr <= 1'b0;
            rep_done <= 1'b0;
            if (!printing) begin
                if (rep_go) begin
                    printing <= 1'b1;
                    r_item <= 5'd0; r_ch <= 5'd0;
                end
            end else if (!u_busy && !p_wr) begin
                p_wr   <= 1'b1;
                p_data <= r_char;
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
        .wr(p_wr || f_wr), .data(p_wr ? p_data : f_data),
        .tx(ftdi_rxd), .busy(u_busy)
    );

    // ------------------------------------------------- 440 Hz test tone ---
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
