"""Budget reservations include queued, in-flight, uncertain, failed and canceled calls."""
from sqlalchemy import select
from .db import Job


class BudgetService:
    def total(self, session, project_id):
        return sum(j.reported_cost if j.reported_cost is not None else j.estimated_cost
                   for j in session.scalars(select(Job).where(Job.project_id == project_id)))
    def reserve(self, session, project, estimate):
        # Caller holds the project row lock; even separate API processes serialize here.
        if estimate is None:
            raise ValueError('No reliable cost estimate configured. Set a conservative provider rate before enabling live requests.')
        if estimate < 0:
            raise ValueError('Cost rate cannot be negative')
        if self.total(session, project.id) + estimate > project.settings['spending_limit'] + 1e-8:
            raise ValueError('Spending limit exceeded, including pending and uncertain requests')
