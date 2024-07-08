from marshmallow import Schema, fields, validate

class ContributionsSchema(Schema):
    username= fields.Str(required=True)
    duration_months = fields.Int(required=True, validate=validate.Range(min=1))
    repo= fields.Str(required=False)