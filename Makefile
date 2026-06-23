load:
	py src/etl/loader.py

ratios:
	py src/analytics/ratios.py

test:
	py -m pytest tests/ --html=reports/pytest_report.html

report:
	py src/reports/portfolio_report.py

dashboard:
	streamlit run src/dashboard/app.py

api:
	uvicorn src.api.main:app --port 8000

clean:
	@echo Cleaning pyc files and caches...