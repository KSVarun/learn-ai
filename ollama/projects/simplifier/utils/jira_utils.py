def create_jira_task_from_local_CSV_file(csvPath:str):
    df = pd.read_csv(csvPath)
    created_jira = []
    for index, row in df.iterrows():
        if pd.notna(row['summary']) and pd.isna(row['jira']):
            fields = {'project':{'key':'AN30'},'issuetype': {'name': 'Task'},'summary': row['summary'], 'description':row['description'], 'assignee':{'id':row['assignee']}}

            # jira_issue_response will contain {'id': '2784859', 'key': 'AN30-6067', 'self': 'link to the json response'}
            jira_issue_response=jira.issue_create(fields)

            updated_jira_issue_response=jira_issue_response
            updated_jira_issue_response['title']=row['summary']
            created_jira.append(updated_jira_issue_response)
            df.at[index, 'jira'] = f'https://amagiengg.atlassian.net/browse/{jira_issue_response['key']}'
    df.to_csv(csvPath, index=False)
    return created_jira