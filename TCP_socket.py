from TCP_socket_p2 import TCP_Connection

class TCP_Connection_Final(TCP_Connection):
	"""docstring for TCP_Connection_Final"""
	def __init__(self, self_address, dst_address, self_seq_num, dst_seq_num, log_file=None):
		super().__init__(self_address, dst_address, self_seq_num, dst_seq_num, log_file)
	def handle_timeout(self):
		#put code to handle RTO timeout here
		#send a single packet containing the oldest unacknowledged data
		#increase the RTO timer 
		# -----------------------
		# Task 3: Resend one packet containing the oldest unacknowledged data
		# Increase the RTO timer
		if self.unacked_packets:
			oldest_unacked_seq = self.unacked_packets[0][0]
			self._packetize_and_send(oldest_unacked_seq, b'')
			self.rto_timer *= 2

	def handle_window_timeout(self):
		#put code to handle window timeout here
		#in other words, if we haven't sent any data in while (which causes this time to go off),
		#send an empty packet
		# -----------------------
		# Task 7: Send an empty packet when the window timer goes off
		if self.last_sent_seq is not None:
			self._packetize_and_send(self.last_sent_seq, b'')

	def receive_packets(self, packets):
		#insert code to deal with a list of incoming packets here
		#NOTE: this code can send one packet, but should never send more than one packet
		# -----------------------
		# Task 1: Receive packets and store them in the receive buffer correctly
		# Task 2a: Set the RTT timer if new data is sent and the timer is not running
		# Task 2b: Update the RTT measurement when sent data is acknowledged and use it for RTO updates
		# Task 4: Update SND.WND when a new window measurement comes in
		# Task 5b: Mark a byte with PSH in the receive buffer if the packet has the PSH flag set
		# Task 6: Send appropriate acknowledgments when new data is received
		#         and update the next expected byte (RCV.NXT) when necessary
		
		for packet in packets:
			seq_num, data, flags = packet
			self.receive_buffer[seq_num - self.receive_buffer_start_seq] = (data, flags)
			if self.receiving_ack_num is None or self.receiving_ack_num < seq_num:
				self.receiving_ack_num = seq_num
				
			if b'PSH' in flags:
				self.push_flag_set = True
				
			if seq_num == self.next_expected_seq_num:
				self.next_expected_seq_num += len(data)
				
			# Send appropriate acknowledgments
			if self.push_flag_set or b'ACK' in flags or len(data) == 0:
				self._send_acknowledgment()
	def send_data(self, window_timeout = False, RTO_timeout = False):
		#put code to send a single packet of data here
		#note that this code does not always need to send data, only if TCP policy thinks it makes sense
		#if there is any data to send, i.e. we have data we have not sent and we are allowed to send by our
		#congestion and flow control windows, then send one packet of that data
		# -----------------------
		# Task 0: Send packets with the largest allowed size based on 3 factors
		# Task 2: Update the congestion control window based on RFC
		# Task 2a: Set the RTT timer if new data is sent and the timer is not running
		# Task 2b: Update the RTT measurement when sent data is acknowledged and use it for RTO updates
		# Task 4: Ensure not to send more data than the flow control window
		# Task 5a: Set the push flag whenever at least one byte is marked PSH in the data to be sent
		# Task 7: Restart the window timer whenever data is sent, including retransmissions
		
		# Get the maximum packet size allowed based on 3 factors
		max_packet_size = min(self.SND.MSS, self.SND.WND, self.congestion_window)
		
		if RTO_timeout:
			# If RTO timeout, resend the oldest unacknowledged packet
			if self.unacked_packets:
				oldest_unacked_seq = self.unacked_packets[0][0]
				self._packetize_and_send(oldest_unacked_seq, b'')
				self.rto_timer *= 2
		else:
			if not window_timeout and max_packet_size > 0:
				# If not window timeout and there is data to send, send one packet of data
				data_to_send = self.send_buffer[:max_packet_size]
				self.send_buffer = self.send_buffer[max_packet_size:]
				self._packetize_and_send(self.snd_nxt, data_to_send)
				self.snd_nxt += len(data_to_send)
				
				if len(data_to_send) > 0:
					# Restart the window timer whenever data is sent, including retransmissions
					self.window_timer = self.rto_timer
					
				if self.snd_nxt == self.snd_una:
					# Set the RTT timer if new data is sent and the timer is not running 
					self._set_rtt_timer()