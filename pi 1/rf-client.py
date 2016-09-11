import bluetooth

while(1):
    bd_addr = "B8:27:EB:C8:2B:9C"

    port = 1

    sock = bluetooth.BluetoothSocket( bluetooth.RFCOMM )
    sock.connect((bd_addr, port))

    sock.send("hello world")

    sock.close()
