"""Pure read-only index filtering: exact structured values, substring text."""


def filter_runs(rows, *, result=None, run_id=None, test_id=None,
                software_version=None, date=None, role=None, min_score=None):
    selected=list(rows)
    for key,value in [('result',result),('run_id',run_id)]:
        if value is not None:
            selected=[row for row in selected if row.get(key)==value]
    for key,value in [('scenario_id',test_id),('software_version',software_version),('date',date)]:
        if value:
            selected=[row for row in selected if value in str(row.get(key,''))]
    if role:
        selected=[row for row in selected if any(role.lower() in str(row.get(key,'')).lower()
                  for key in ('persona','executor','reviewer'))]
    if min_score is not None:
        selected=[row for row in selected if row.get('scores') and min(row['scores'].values())>=min_score]
    return selected
