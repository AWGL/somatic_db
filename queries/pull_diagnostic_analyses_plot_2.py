# Description:
# Pull out all diagnostic analyses from 2021 to present, filter to TSO500_DNA and TSO500_RNA and plot by panel and month uploaded.
# Save tables of the grouped data.
# 
# Date: 15/04/2025 - AW
# Use: python manage.py shell < pull_diagnostic_analyses_plot_2.py (with plotly env activated)
# Plots (html files) and tables (csv files) saved to queries folder

import pandas as pd
from django.db.models import Count
from analysis.models import SampleAnalysis
import datetime
import pytz
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

start_date = datetime.datetime(2021, 1, 1, tzinfo=pytz.UTC)

# Django query to pull out SampleAnalyses and the panel they were run on
sample_analyses = SampleAnalysis.objects.filter(
    worksheet__diagnostic=True
).values(
    'panel__pretty_print',
    'worksheet__upload_time',
    'worksheet__assay',
    'worksheet__run__run_id',
    'sample',
)
#).annotate(count=Count('id'))

# Convert query result to a DataFrame
data = pd.DataFrame(list(sample_analyses))

# Extract month and year from upload_time
data.sort_values(by="worksheet__run__run_id",inplace=True)
print(f"rows data {data.shape[0]}")
print(data.head(20))
print(data.tail(20))

# create add year_month and formatted_date to dataframe
dated = pd.DataFrame()
for i, row in data.iterrows():
    year = int(f"20{row['worksheet__run__run_id'][:2]}")
    month = int(row['worksheet__run__run_id'][2:4])
    day = int(row['worksheet__run__run_id'][4:6])
    date = datetime.datetime(year, month, day, tzinfo=pytz.UTC)
    row['year_month'] = date
    row['formatted_date'] = date.strftime('%Y-%m')
    dated = dated._append(row, ignore_index=True)

# filter to runs since Jan 2021
print(f"rows dated {dated.shape[0]}")
dated = dated.loc[dated["year_month"] > start_date, :]
print(f"rows dated filtered {dated.shape[0]}")

dated = dated.loc[(dated["worksheet__assay"] == "TSO500_DNA") | (dated["worksheet__assay"] == "TSO500_RNA"),:]
print(f"rows dated filtered by assay  {dated.shape[0]}")
data_DNA = dated.loc[dated["worksheet__assay"] == "TSO500_DNA",:]
print(f"rows data_DNA{data_DNA.shape[0]}")
data_RNA = dated.loc[dated["worksheet__assay"] == "TSO500_RNA",:]
print(f"rows data_RNA{data_RNA.shape[0]}")

print("filtered")
print(dated.head(20))
print(dated.tail(20))

# Group by month and panel, and count occurrences
grouped_DNA = data_DNA.groupby(['formatted_date', 'panel__pretty_print']).size().reset_index(name='Count')
grouped_RNA = data_RNA.groupby(['formatted_date', 'panel__pretty_print']).size().reset_index(name='Count')

grouped_DNA.to_csv("/u02/temp/Ant/TSO500_DNA_diagnostic_analyses_table.csv")
grouped_RNA.to_csv("/u02/temp/Ant/TSO500_RNA_diagnostic_analyses_table.csv")

panels_DNA = data_DNA["panel__pretty_print"].unique()
panels_RNA = data_RNA["panel__pretty_print"].unique()

assays = {
    "TSO500 DNA": [data_DNA, panels_DNA],
    "TSO500 RNA": [data_RNA, panels_RNA],
    }

for label, data in assays.items():

    fig = go.Figure()
    df = data[0]
    panels = data[1]

    for panel in panels:
        slice = df.loc[df["panel__pretty_print"]==panel,:]
        array = np.array(slice["formatted_date"])
        fig.add_trace(go.Histogram(name=panel,x=array))

    # modify plot appearance
    fig.update_layout(
        barmode='stack',
        title_text=f"{label} diagnostic runs over time",
        xaxis_title_text="Month",
        yaxis_title_text="Run count",
        dragmode="zoom",
        hovermode="x",
        template="plotly_white",
        margin=dict(
            t=100,
            b=100,
        )
    )

    # Add range slider
    fig.update_layout(
        xaxis=go.layout.XAxis(
            rangeselector=dict(
                buttons=list([
                    dict(count=1,
                         label="1m",
                         step="month",
                         stepmode="backward"),
                    dict(count=6,
                         label="6m",
                         step="month",
                         stepmode="backward"),
                    dict(count=1,
                         label="YTD",
                         step="year",
                         stepmode="todate"),
                    dict(count=1,
                         label="1y",
                         step="year",
                         stepmode="backward"),
                    dict(step="all")
                ])
            ),
            rangeslider=dict(
                visible=True
            ),
            type="date"
        )
    )

    # calculate monthly run totals
    month_totals = []
    months = df["formatted_date"].unique()
    for month in months:
        month_slice = df.loc[df["formatted_date"]==month]
        month_total = month_slice.shape[0]
        month_totals.append(month_total)
    print(label)
    print(month_totals)

    # add monthly totals to figure
    fig.add_trace(go.Scatter(
        x=months,
        y=month_totals,
        text=month_totals,
        mode='text',
        textposition='top center',
        textfont=dict(
            size=12,
        ),
        showlegend=False
    ))

    fig.write_html(f"/u02/temp/Ant/{label.replace(' ','_')}_plot.html")
 