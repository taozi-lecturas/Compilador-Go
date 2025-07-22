
qemu-arm ./output/ejemplo_saludo_armv7
readelf -A output/ejemplo_saludo_armv7 | grep -i arch 

qemu-arm ./output/ejemplo_completo_armv7
readelf -A output/ejemplo_completo_armv7 | grep -i arch 

qemu-arm ./output/ejemplo_bool_armv7
readelf -A output/ejemplo_bool_armv7 | grep -i arch 

