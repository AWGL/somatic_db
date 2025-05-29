# SVD developer guide - Quick install

## Setting up a local version of the database

Clone the repository, change to the directory, set up environment:

```
git clone https://github.com/AWGL/somatic_db.git
cd somatic_db
conda env create -f env.yaml
conda activate somatic_variant_db
```

Make sure that the `DB_INSTANCE` variable within `somatic_variant_db/settings.py` is set to `local` so that the app uses sqlite3 rather than postgres (postgres is used in live database):

Line 83 `somatic_variant_db/settings.py`:
```
DB_INSTANCE = 'local'
```

Set up local database:
```
python manage.py makemigrations
python manage.py migrate
```

Optional - Sometimes the models for the analysis app wont be created automatically by Django, if that happends then run this:
```
python manage.py makemigrations analysis
python manage.py migrate
```

Create the superuser, this should be called `admin` to work with upload scripts:
```
python manage.py createsuperuser
```

Load fixtures for the panels and variant list objects:
```
python manage.py loaddata panels.json
python manage.py loaddata variant_lists.json
```

Optional - Load in poly lists (`--both_checks` flag will bypass the need for two checks on each poly, for dev work only):
```
python manage.py add_poly_list --list build_37_polys --variants roi/b37_polys.txt --both_checks
python manage.py add_poly_list --list build_38_polys --variants roi/b38_polys.txt --both_checks
```

Optional - Load in test cases:
```
bash scripts/upload.sh analysis/test_data/Database_37/samples_dna_ws_1.csv run_1
bash scripts/upload.sh analysis/test_data/Database_37/samples_dna_ws_2.csv run_2
bash scripts/upload.sh analysis/test_data/Database_37/samples_rna_ws_1.csv run_1
bash scripts/upload.sh analysis/test_data/Database_37/samples_ctdna_ws_1.csv
bash scripts/upload.sh analysis/test_data/Database_38/samples_database_test38_DNA.csv
bash scripts/upload.sh analysis/test_data/Database_37/samples_crm_ws_1.csv run_3
```

Run the database locally:
```
python manage.py runserver
```

Setup user groups:
- Within the admin page, click on Authentication and Authorization > Groups
- Make a new group called qc_signoff
- This user group is to allow users to signoff the QC and is intended for the bioinformatics team

Add users to user group:
- Within the admin page, click on Authentication and Authorization > Users
- Under the Groups section, add the qc_signoff group for that user and click save

!> You may get a Django error when clicking into a sample analysis that ends with the following:
`django.contrib.auth.models.User.usersettings.RelatedObjectDoesNotExist: User has no usersettings.`
In this case, click into the User model within the admin page and make sure there is something in the 'LIMS initials' field at the bottom.
