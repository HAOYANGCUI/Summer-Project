import bluetooth

while(1):
    bd_addr = "00:15:83:D1:BD:DB"

    port = 1

    sock = bluetooth.BluetoothSocket( bluetooth.RFCOMM )
    sock.connect((bd_addr, port))

    sock.send('12321')

    sock.close()
