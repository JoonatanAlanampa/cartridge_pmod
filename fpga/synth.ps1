# synth.ps1 - build the Cartridge Pmod bring-up bitstream for the ULX3S 85F.
#   powershell -File fpga\synth.ps1
# Output: fpga\build\cartridge_bringup.bit
# Flash:  openFPGALoader -b ulx3s fpga\build\cartridge_bringup.bit
# Needs the OSS CAD Suite in ~\opt\oss-cad-suite (same as the CPU/CORDIC projects).
$ErrorActionPreference = "Stop"
$oss = "$env:USERPROFILE\opt\oss-cad-suite"
$env:PATH = "$oss\bin;$oss\lib;" + $env:PATH
# relative paths: the user profile path contains a space, which yosys'
# script parser will not forgive
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force fpga\build | Out-Null

yosys -q -p "read_verilog -sv fpga/spi_byte.sv fpga/uart_tx.sv fpga/bringup_top.sv; synth_ecp5 -top bringup_top -json fpga/build/bringup.json"
if ($LASTEXITCODE -ne 0) { throw "yosys failed" }

nextpnr-ecp5 --85k --package CABGA381 --json fpga/build/bringup.json `
    --lpf fpga/ulx3s.lpf --textcfg fpga/build/bringup.config
if ($LASTEXITCODE -ne 0) { throw "nextpnr failed" }

ecppack fpga/build/bringup.config fpga/build/cartridge_bringup.bit
if ($LASTEXITCODE -ne 0) { throw "ecppack failed" }

Write-Output "OK: fpga\build\cartridge_bringup.bit"
