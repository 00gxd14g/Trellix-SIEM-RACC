from main import create_app
from models.customer import db, Rule

app = create_app()

with app.app_context():
    rules = Rule.query.all()
    print(f"Total rules: {len(rules)}")
    for rule in rules[:5]:
        print(f"Rule ID: {rule.id}, NormID: {rule.normid}, SID: {rule.sid}, Class: {rule.rule_class}")
