from TCP_socket_p2 import TCP_Connection
from TCP_socket_p2 import TCP_Segment
from typing import List
from threading import current_thread

g_reTran = False


class TCP_Connection_Final(TCP_Connection):
	"""docstring for TCP_Connection_Final"""
	def __init__(self, self_address, dst_address, self_seq_num, dst_seq_num, log_file=None):
		super().__init__(self_address, dst_address, self_seq_num, dst_seq_num, log_file)
	
	#------------------------------------------------------------------------------------------------------------------------------
	def handle_timeout(self):
		allow_send_len = min(self.SND.MSS, self.SND.WND, self.congestion_window, len(self.send_buff))
		if allow_send_len <= 0:
			return

		global g_reTran
		g_reTran = True

		PSH_FLAG = False
		data = []
		for i in range(allow_send_len):
			if isinstance(self.send_buff[i], bytes):
				PSH_FLAG = True
				data.append(self.send_buff[i][0])
			else:
				data.append(self.send_buff[i])
		

		self._packetize_and_send(self.SND.UNA, PSH_FLAG, bytes(data))
		
		self.last_packet[:]= [self.SND.UNA, PSH_FLAG, bytes(data)]

		self.RTO_timer.set_and_start(self.RTO_timer.timer_length * 2)

		pass
	#------------------------------------------------------------------------------------------------------------------------------
	def handle_window_timeout(self):
		global g_reTran
		if not g_reTran:
			self._packetize_and_send(self.last_packet[0], self.last_packet[1], self.last_packet[2])

		self.window_timer.set_and_start(self.window_timer.timer_length * 2)
		pass

	#------------------------------------------------------------------------------------------------------------------------------
	def receive_packets(self, packets: List[TCP_Segment]):

		if len(packets) == 0:
			return

		recv_new_bytes = False
		for i in range(len(packets)):

			
			if packets[i].ACK >= self.SND.UNA and packets[i].ACK <= self.SND.NXT:
				if self.SND.WL1 < packets[i].SEQ or (self.SND.WL1 == packets[i].SEQ and self.SND.WL2 <= packets[i].ACK):
					self.SND.WND = packets[i].WND
					self.SND.WL1 = packets[i].SEQ
					self.SND.WL2 = packets[i].ACK
				else:
					continue
			else:
				continue

			if len(packets[i].data) > 0:
				recv_new_bytes = True

			spare_bytes = len(self.receive_buffer) - (packets[i].SEQ - self.receive_buffer_start_seq)
			if spare_bytes == 0:
				recv_new_bytes = True
				break
			if spare_bytes < len(packets[i].data):
				packets[i].data = packets[i].data[0:spare_bytes]
			
			for j in range(len(packets[i].data)):
				self.receive_buffer[packets[i].SEQ - self.receive_buffer_start_seq + j] = packets[i].data[j]
			if packets[i].flags.PSH:
				self.receive_buffer[packets[i].SEQ - self.receive_buffer_start_seq + len(packets[i].data) - 1] = bytes([packets[i].data[-1]] + list(b'PSH'))
			if packets[i].ACK:
				if packets[i].SEQ + len(packets[i].data) >= self.RCV.NXT:
					self.RTO_timer.reset_timer()
			if packets[i].SEQ + len(packets[i].data) > self.RCV.NXT:
				recv_new_bytes = True
			if packets[i].ACK > self.SND.UNA:
				self.send_buff = self.send_buff[packets[i].ACK - self.SND.UNA:]
				self.SND.UNA = packets[i].ACK
			else:
				pass
			if packets[i].WND <= 0:
				if not self.window_timer.is_runnning():
					pass
			else:
				if self.window_timer.is_runnning():
					self.window_timer.stop_timer()
		seeNone = False
		for i in range(len(self.receive_buffer)):
			if self.receive_buffer[i] == None:
				self.RCV.NXT = i + self.receive_buffer_start_seq
				seeNone = True
				break
		if not seeNone:
			self.RCV.NXT = self.receive_buffer_start_seq + len(self.receive_buffer)
		self.RCV.WND = len(self.receive_buffer) - (self.RCV.NXT - self.receive_buffer_start_seq)
		if recv_new_bytes:
			self._packetize_and_send(seq=self.SND.UNA)
			if self.SND.UNA >= self.SND.NXT:
				self.RTO_timer.stop_timer()
				global g_reTran
				g_reTran = False
		pass

#------------------------------------------------------------------------------------------------------------------------------

	def send_data(self, window_timeout = False, RTO_timeout = False):

		allow_send_len = min(self.SND.MSS, self.SND.WND, self.congestion_window, len(self.send_buff) - (self.SND.NXT - self.SND.UNA))
		if allow_send_len <= 0:
			return

		if self.SND.NXT >= self.SND.UNA + self.SND.WND:
			return
		PSH_FLAG = False
		data = []
		for i in range(allow_send_len):
			if isinstance(self.send_buff[self.SND.NXT - self.SND.UNA + i], bytes):
				PSH_FLAG = True
				data.append(self.send_buff[self.SND.NXT - self.SND.UNA + i][0])
			else:
				data.append(self.send_buff[self.SND.NXT - self.SND.UNA + i])
				self._packetize_and_send(self.SND.NXT, PSH_FLAG, bytes(data))
				self.last_packet[:]= [self.SND.NXT, PSH_FLAG, bytes(data)]
		if not self.RTO_timer.is_runnning():
			self.RTO_timer.set_and_start(1)
		if not self.window_timer.is_runnning():
			self.window_timer.set_and_start(1)
		self.SND.NXT = self.SND.NXT + allow_send_len

		pass

#------------------------------------------------------------------------------------------------------------------------------
