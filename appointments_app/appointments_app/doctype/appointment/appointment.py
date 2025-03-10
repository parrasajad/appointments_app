# Copyright (c) 2023, Build With Hussain and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Appointment(Document):
	def validate(self):
		# validate the contact_number to be a valid 10 digit phone number except the country code, 
		# if it does not have a country code, prepend +91
		if not self.contact_number:
			frappe.throw("Please enter a valid contact number")
		if len(self.contact_number) == 10:
			self.contact_number = f"+91{self.contact_number}"
		elif len(self.contact_number) == 13 and self.contact_number.startswith("+91"):
			pass
		else:
			frappe.throw("Please enter a valid contact number")
		
	def after_insert(self):
		self.queue_number = self.add_to_appointment_queue()
		# attach csrf token + queue number as key and queue number as value
		frappe.cache.set_value(f"{frappe.session.sid}:queue_number", self.queue_number)
		self.save(ignore_permissions=True)
		self.send_confirmation_message()

	def add_to_appointment_queue(self):
		filters = {
			"date": self.date,
			"shift": self.shift,
			"clinic": self.clinic,
		}
		appointment_queue_exists = frappe.db.exists(
			"Appointment Queue",
			filters,
		)

		if appointment_queue_exists:
			q = frappe.get_doc("Appointment Queue", filters)
		else:
			q = frappe.new_doc("Appointment Queue")
			q.update(filters)
			q.save(ignore_permissions=True)

		q.append("queue", {"appointment": self.name, "status": "Pending"})
		q.save(ignore_permissions=True)

		return len(q.queue)

	def send_confirmation_message(self):
		frappe.enqueue(
			"appointments_app.utils.send_message",
			body=f"Appointment Booked! Your queue number is {self.queue_number} at {self.clinic} on {self.date}",
			from_=frappe.db.get_single_value(
				"Appointments Twilio Settings", "from_phone_number"
			),
			to=self.contact_number,
		)
