import requests
import concurrent.futures
import time

# Where to monitor and report number of API calls if not in askCO?

class RequestBundle():
	def __init__(self, submitted_requests=[]):
		self.submitted_requests = submitted_requests
		self.completed_requests = []
		self.complete = False

	def send_bundle(self, resume=False):
		start_time = time.perf_counter()

		with concurrent.futures.ThreadPoolExecutor() as executor:
			futures = []
			for api_request in self.submitted_requests:
				if resume == True:
					if api_request.complete == False:
						futures.append(executor.submit(api_request.send_query()))
				else:
					futures.append(executor.submit(api_request.send_query()))

			for future_request in concurrent.futures.as_completed(futures):
				status = future_request.status_code
				if status == 429:
					self.cooldown()
				else:
					self.completed_requests.append(future_request)


		end_time = time.perf_counter()
		if not config.get("quiet"):
			print("Bundle ran in {} seconds".format(start_time-end_time:0.2f))


	def cooldown(self):
		api_cooled_down = False
		for api_request in self.submitted_requests():
			if not api_request.complete:
				api_request.abort()
		
		while api_cooled_down == False:
			time.sleep(10)
			test_query = Query(method="GET", url=config.get("base_url"))
			if test_query.status_code == 200:
				api_cooled_down = True

		self.send_bundle(resume=True)

	def complete_bundle(self):