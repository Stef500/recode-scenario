import pandas as pd
import numpy as np
import datetime as dt
import re
import datetime
import random
import yaml
import pyarrow.parquet as pq


from os import listdir
from os.path import isfile

# Usefull functions



def random_date(year,exclude_weekends=False):
  """   
  Generates a random date in the year 2024.

  Args:
    exclude_weekends: If True, excludes Saturdays and Sundays.
  """

  while True:

    month = random.randint(1, 12)
    # Get the number of days in the randomly chosen month
    if month == 2:
      if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0): # Check for leap year
        day = random.randint(1, 29)
      else:
        day = random.randint(1, 28)
    elif month in [4, 6, 9, 11]:
      day = random.randint(1, 30)
    else:
      day = random.randint(1, 31)

    random_date = datetime.date(year, month, day)

    if exclude_weekends:
      if random_date.weekday() < 5:  # Monday is 0, Sunday is 6
        break
    else:
      break
  return random_date


def random_date_between(start_date, end_date):
    """
    Generates a random date between two datetime.date objects (inclusive).
    """

    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates + 1)
    random_date = start_date + datetime.timedelta(days=random_number_of_days)
    return random_date

def get_dates_of_stay(admission_type: str=None,
                      admission_mode: str=None,
                      mols:  float | None = None,
                      sdlos: float| None = None,
                      los: int| None= None,
                      year : int= None ):
    """
    Generate date of entry and date of discharge from Mean Length of Stay (MLOS) and Standard Deviaton length of stay (DSLOS)
    """

    if admission_type == "Outpatient" :
        date_entry = date_discharge = random_date(years,exclude_weekends=False)

    else : 
        if los == None:
            # los can be negative if we do like this
            #los = int(np.round(np.random.normal(mols, sdlos, 1))[0]) 
            
            los = int(np.abs(np.random.normal(mols, sdlos, 1)[0])) 


        if admission_mode=="URGENCES":
            date_entry = random_date(year,exclude_weekends=False)
        else :
            date_entry = random_date(year,exclude_weekends=True)

        date_discharge = date_entry + datetime.timedelta(days=los)

    return date_entry, date_discharge


def extract_integers_from_cage(cage_string):
    """
            Extraction first and second age from age categorie
            
            Extracts integer values from a string 
            in the format "[x-y[" or "[x-[" and considers y as 90 if missing.
            
    """
    match = re.match(r"\[(\d+)-(\d+)\[", cage_string.strip())
    if match:
        return [int(match.group(1)), int(match.group(2))]
    else:
        # Handle the case for "[x-[" format like "[80-["
        match_single = re.match(r"\[(\d+)-\[", cage_string.strip())
        if match_single:
            return [int(match_single.group(1)), 90] # Consider missing y as 100
        else:
            return [] # Return empty list if no match

def get_age(cage):
    """
    Get random age from age categorie

    """
    age_min,age_max = extract_integers_from_cage(cage)
    return random.randint(age_min, age_max)

def interpret_sexe(sexe):
  if sexe == 1: return "Masculin"
  else: return "Féminin"

def prepare_prompt(prompt_path, case):
  with open(prompt_path, "r", encoding="utf-8") as f:
      content = f.read()
  return (content
          .replace("[SCENARIO here]", case["SCENARIO"])
          .replace("[INSTRUCTIONS_CANCER here]", case["INSTRUCTIONS_CANCER"])
          # .replace("[ICD_ALTERNATIVES here]", case["ICD_ALTERNATIVES"])
          )
  
def weighted_code_sample(self,code):
    
    if code in self.icd_categ_weight:

        return random.choices(population=self.icd_categ_weight[code]["code"],
                              weights=self.icd_categ_weight[code]["weight"],
                              k=1)[0]
    else:
        return code  # Retourne le code original si la catégorie n'existe pas
class generate_scenario:

    def __init__(self,
                 path_ref : str = "referentials/",
                 path_data : str = "data/",
                 grouping_secondary_diag :list = ["sexe","cage2","drg_parent_code","icd_primary_code"]):

        """
        Generate scenario from DRG statistics
        

        Steps :
        - ...


        Parameters
        ----------
        - params : 
        """

        self.name = "bed_capacity_gilda_extraction_management"
        self.description = "Import and preprocess GILDA extraction data for further update of the bedcapacity table."

        #Params

        self.path_ref = path_ref
        self.path_data = path_data
        self.grouping_secondary_diag = grouping_secondary_diag
        self.simulations_years = [dt.date.today().year-2,dt.date.today().year-1,dt.date.today().year]

        # Recoding french names
        #TODO : other variables : adminission mode
        self.recoding_dict ={"HP":"Outpatient","HC":"Inpatient"}
        
        self.icd_codes_cancer_meta_ln= ["C770","C771","C772","C773","C774","C775","C778","C779"]
        self.icd_codes_cancer_meta = ["C780","C781","C782","C783","C784","C785","C786","C787","C788",
                    "C790","C791","C792","C793","C794","C795","C796","C797","C798"]
        
        self.icd_codes_contact_tt_rep = ["Z491","Z511","Z512","Z5101","Z513","Z516"]

        self.idc_code_chmio_non_tum = ["Z512"]

        self.drg_parent_code_chimio = ['28Z07','17M05','17M06']
        self.drg_parent_code_radio = ["17K04","17K05","17K08","17K09","28Z10","28Z11","28Z18","28Z19",
                        "28Z20","28Z21","28Z22","28Z23","28Z24","28Z25"]
        self.icd_codes_t2_chronic_intractable_pain = ["R5210","R5218"]
        self.icd_codes_ascites = ["R18"]
        self.icd_codes_pleural_effusion = ["J90", "J91", "J940","J941","J942","J948","J949"]
        self.icd_codes_cosmetic_surgery = ["Z410","Z411"]
        self.icd_codes_comfort_intervention = ["Z4180"]
        
        self.icd_codes_plastic_surgery = ["Z420","Z421","Z423","Z424","Z425","Z426","Z427","Z428","Z429"]
        
        self.icd_codes_prophylactic_intervention = ["Z400","Z401","Z408"]

        self.drg_parent_code_greffe = ["27Z02","27Z03","27Z04"]
        self.drg_parent_code_transfusion = ["28Z14"]
        self.drg_parent_code_palliative_care = ["23Z02"]
        self.drg_parent_code_stomies = ["06M17"]
        self.drg_parent_code_apheresis = ["28Z16"]
        self.drg_parent_code_deceased = ["04M24"]
        self.drg_parent_code_bilan = ["23M03"]

        #---- DRG parents groups delivery

        self.drg_parents_groups_vaginal_delivery = ["14C03","14Z09","14Z10","14Z11","14Z12","14Z13","14Z14"]
        self.drg_parents_groups_csection = ["14C06","14C07","14C08"]
        self.drg_parents_groups_delivery = self.drg_parents_groups_vaginal_delivery + self.drg_parents_groups_csection

        #--- Procdure delivery
        self.procedure_vaginal_delivery = ["JQGD001", "JQGD002","JQGD003","JQGD004","JQGD005","JQGD007","JQGD008","JQGD010","JQGD012","JQGD013"]
        self.procedure_csection = ["JQGA002","JQGA003","JQGA004","JQGA005"]

        self.icd_codes_cancer = pd.read_excel(path_ref + "REFERENTIEL_METHODE_DIM_CANCER_20140411.xls")
        self.icd_codes_cancer = self.icd_codes_cancer.CIM10.to_list()
        # Add icd_parent_code to list, but not very elgant, it will be usefull as some of icd codes that will tested to be 
        # in that list are actualy icd_parent_code
        #TODO : Find an other way...
        self.icd_codes_cancer = list(set([code[0:3] for code in self.icd_codes_cancer])) + self.icd_codes_cancer
        self.icd_codes_cancer = [ code for code in self.icd_codes_cancer if code[0:1]!="Z"]
        self.drg_statistics = pd.read_excel(path_ref + "stat_racines.xlsx")
        self.drg_statistics.rename(columns = {"racine":"drg_parent_code","dms":"los_mean","dsd":"los_sd"},inplace=True)

        self.df_icd_synonyms = pd.read_csv(path_ref + "cim_synonymes.csv").dropna()
        self.df_icd_synonyms.rename(columns = {"dictionary_keys":"icd_code_description","code":"icd_code"},inplace=True)

        self.df_chronic = pd.read_excel(path_ref + "Affections chroniques.xlsx",header=None,names=["code","chronic","libelle"])
        self.df_chronic.loc[self.df_chronic.code.isin(self.icd_codes_cancer),"chronic"]=3
        self.icd_codes_chronic = self.df_chronic.code[self.df_chronic.chronic.isin([1,2,3])].to_list()

        self.df_complications = pd.read_csv(path_ref + "cma.csv").dropna()

        self.drg_parents_groups = pd.read_excel(self.path_ref + "ghm_rghm_regroupement_2024.xlsx")
        self.drg_parents_groups.rename(columns={"racine":"drg_parent_code","libelle_racine":"drg_parent_description"},inplace=True)

        self.df_names = pd.read_csv(path_ref + "prenoms_nom_sexe.csv",sep=";").dropna()


        self.icd_codes_chronic_attack = pd.read_csv(path_ref + "icd_codes_chronic_attack.csv",sep=";").code.to_list()
        
        #TODO complications of chronic diseases
        self.icd_codes_chronic_complications = None
        #--- Loading parameters file
        self.procedure_botulic_toxin = pd.read_csv(path_ref + "procedure_botulic_toxine.csv",sep=";").code.to_list()
        
        self.icd_codes_prophylactic_intervention = pd.read_csv(path_ref + "icd_codes_prophylactic_intervention.csv",sep=";").code.to_list()
        
        self.attention_artificial_openings_external_prosthetic_device = pd.read_csv(path_ref + "attention_artificial_openings_external_prosthetic_device.csv",sep=";").code.to_list()
        
        self.icd_codes_iron_deficiency_anemia = pd.read_csv(path_ref + "icd_codes_iron_deficiency_anemia.csv",sep=";").code.to_list()
        
        self.icd_codes_sessions = pd.read_csv(path_ref + "icd_codes_sessions.csv",sep=";").code.to_list()
        
        self.icd_codes_diabetes_chronic = pd.read_csv(path_ref + "icd_codes_diabetes_chronic.csv",sep=";").code.to_list()
        
        self.icd_codes_spontaneous_vertex_delivery = pd.read_csv(path_ref + "icd_codes_spontaneous_vertex_delivery.csv",sep=";").code.to_list()
        
        self.icd_codes_liveborn_infants = pd.read_csv(path_ref + "icd_codes_liveborn_infants.csv",sep=";").code.to_list()
        
        self.icd_codes_medical_abortion =  pd.read_csv(path_ref + "icd_codes_medical_abortion.csv",sep=";").code.to_list()
        
        self.icd_codes_legal_abortion =  pd.read_csv(path_ref + "icd_codes_legal_abortion.csv",sep=";").code.to_list()
        
        self.icd_codes_supervision = pd.read_csv(path_ref + "icd_codes_supervision.csv",sep=";").code.to_list()
        
        self.icd_codes_supervision_chronic_disease = pd.read_csv(path_ref + "icd_codes_supervision_chronic_disease.csv",sep=";").code.to_list()
        
        self.icd_codes_surgical_followup = pd.read_csv(path_ref + "icd_codes_surgical_followup.csv",sep=";").code.to_list()
        
        self.icd_codes_supervision_pregnancy = pd.read_csv(path_ref + "icd_codes_supervision_pregnancy.csv",sep=";").code.to_list()
        
        self.icd_codes_supervision_post_partum =  pd.read_csv(path_ref + "icd_codes_supervision_post_partum.csv",sep=";").code.to_list()
        
        self.icd_codes_cardic_vascular_implants = pd.read_csv(path_ref + "icd_codes_cardic_vascular_implants.csv",sep=";").code.to_list()

        self.icd_codes_overnight_study = pd.read_csv(path_ref + "icd_codes_overnight_study.csv",sep=";").code.to_list()
        
        self.icd_codes_sensitization_tests = pd.read_csv(path_ref + "icd_codes_sensitization_tests.csv",sep=";").code.to_list()
        
        self.icd_codes_preoperative_assessment =  pd.read_csv(path_ref + "icd_codes_preoperative_assessment.csv",sep=";").code.to_list()
        
        self.icd_codes_family_history = pd.read_csv(path_ref + "icd_codes_family_history.csv",sep=";").code.to_list()
     
        self.icd_codes_personnel_history =  pd.read_csv(path_ref + "icd_codes_personnel_history.csv",sep=";").code.to_list()
        
        #--- Exclusions
        self.icd_exclusions = ["Z40","Z08","Z09","Z48","Z71","Z48","Z34","Z35","Z39","Z94","Z95","Z94","Z96","Z3908","Z762"]
        self.exclusion_specialty = ["THERAPIE TRANSFUSION","PSYCHIATRIE INFANTO-JUVENILE NON SECTORISE","PHYSIOLOGIE","PHYSIOLOGIE PEDIATRIQUE"]

        # Import of coding rules
        fichier_yaml = "templates/regles_atih.yml"
        with open(fichier_yaml, "r", encoding="utf-8") as fichier:
            rules = yaml.safe_load(fichier)

        self.coding_rules={}
        for d in rules["regles"] :
            self.coding_rules[d["id"]] = {"texte": d["clinical_coding_scenario"], "criteres" : d["classification_profile_criteria"] }
            
        # DataFrame to load scenarios
        self.df_classification_profile = pd.DataFrame()
     
    def load_offical_icd(self,
                        file_name : str,
                        col_names: [] ):

        df_icd = pd.read_csv(self.path_ref + file_name, sep="|",
                                header=None,
                                names=col_names,
                                encoding="latin-1")
        
        df_icd.code = df_icd.icd_code.str.replace(" ","")
        self.df_icd_valid = df_icd.loc[df_icd.aut_mco!=3,["icd_code","icd_code_description"]]
        self.df_icd_official = df_icd[["icd_code","icd_code_description"]]
        
        self.df_term_icd  =self.df_icd_valid[~(self.df_icd_valid.icd_code.isin(self.df_complications.icd_code))]
        self.df_term_icd = self.df_term_icd.assign(categ  =self.df_term_icd.icd_code.str.slice(0,3))
        
        
    def load_icd_categ_weight(self,
                        file_name : str,
                        col_names: [] ):
        

        df_icd_categ_weight = pd.read_csv(self.path_ref + file_name,sep=";",decimal=",")
        
        if col_names is not None : 
            df_icd_categ_weight.rename(columns = col_names, inplace = True) 
            
        categ_9 = df_icd_categ_weight.loc[(df_icd_categ_weight.icd_code.str.slice(-1)=="9")& (df_icd_categ_weight.weight>80) & (df_icd_categ_weight.icd_code.isin(self.df_icd_valid.icd_code)),"categ"]
        df_icd_categ_weight = df_icd_categ_weight.assign(weight = np.where(  (df_icd_categ_weight.icd_code.str.slice(-1)=="9") & (~ df_icd_categ_weight.categ.isin(categ_9)) ,0.5,df_icd_categ_weight.weight))
        icd_categ_weight = df_icd_categ_weight[~(df_icd_categ_weight.icd_code.isin(self.df_complications.icd_code))].groupby(["categ"]).agg(list).drop( columns= ["nb","nb_categ"]).reset_index()
        self.icd_categ_weight = icd_categ_weight.set_index("categ").to_dict(orient="index")

            
    def load_offical_procedures(self,
                        file_name : str,
                        col_names: dict | None = None ):
        
        self.df_procedure_official =  pd.read_excel(self.path_ref + file_name )

        if col_names is not None : 
            self.df_procedure_official.rename(columns = col_names, inplace = True) 

        self.pathology_procedure = self.df_procedure_official.procedure[self.df_procedure_official.procedure_description.str.contains("Examen anatomopathologique")]

        
    def load_cancer_treatement_recommandations(self,
                        file_name : str,
                        col_names: dict | None = None ):
        
        self.df_cancer_treatment_recommandation =  pd.read_excel(self.path_ref + file_name )

        if col_names is not None : 
            self.df_cancer_treatment_recommandation.rename(columns = col_names, inplace = True) 

    def load_specialty_refential(self,
                        file_name : str,
                        col_names: dict | None = None ):
        
        self.ref_sep = pd.read_excel(self.path_ref + file_name)

        if col_names is not None : 
           self.ref_sep.rename(columns = col_names, inplace = True) 

        self.ref_sep = self.ref_sep[~self.ref_sep.specialty.isin(self.exclusion_specialty)]

    def load_classification_profile(self,
                       file_name : str,
                       col_names: dict | None = None ,
                       replace : bool = True):

        table= pq.read_table("data/" + file_name)
        df =  table.to_pandas()
        df.reset_index(inplace=True)
        
        if col_names is not None : 
            df.rename(columns = col_names, inplace = True) 
        
        if self.icd_exclusions is not None :        
            df = df[(~ (df.icd_primary_code.str.slice(0,3).isin(self.icd_exclusions) ) )  & 
                    (~ (df.case_management_type.str.slice(0,3).isin(self.icd_exclusions)) ) ]
        #Split codes in str format into list
        df = df.assign( icd_secondary_code =df.icd_secondary_code.apply(
                                lambda x: [] if x == "" else x.split() ))
        if "los" not in df.columns :
            df = df.merge(self.drg_statistics,how="left")
            df = df.assign(los_mean = np.where(df.los_mean.isna(),0,df.los_mean) )
            df = self.df.assign(los_sd = np.where(df.los_sd.isna(),0,df.los_sd) )

        ### Add DRG groups : 
        df= df.merge(self.drg_parents_groups,how="left")
        df = df.assign(admission_type = df.admission_type.replace(self.recoding_dict))
        
        ### Add medical speciality
        df = df.merge(self.ref_sep[["age","specialty","drg_parent_code"]],how="left")

        if len(self.df_classification_profile) !=0  and replace!= True:
            self.df_classification_profile = pd.concat([self.df_classification_profile,df.copy()])
        else:
            self.df_classification_profile = df.copy()


    def load_referential_hospital(self,
                       file_name : str,
                       col_names: list = ["hospital"] ):
        
        self.df_hospitals = pd.read_csv(self.path_ref+ file_name, names = col_names)

    def load_exclusions(self,
                       file_name : str,
                       col_names: dict | None = None):
        
        self.df_exclusions = pd.read_csv(self.path_ref+ file_name)

        if col_names is not None : 
            self.df_exclusions.rename(columns = col_names, inplace = True) 


    def load_secondary_icd(self,
                       file_name : str,
                       col_names: dict | None = None  ):
        """
        Related diagnosis are segmented in chronical deseases and complications (acute diseases). 
        For cancer we build specific categories : primitive, lymph node metastasis, other metastasis.

        To facilitate sample among related diagnosis, we calculate for each sitution the total number of possible related diagnosis.

        """
        self.df_secondary_icd = pd.read_csv(self.path_data + file_name ,sep=";")

        if col_names is not None : 
            self.df_secondary_icd.rename(columns = col_names, inplace = True)

        self.df_secondary_icd = self.df_secondary_icd.assign(type = np.where(self.df_secondary_icd.icd_secondary_code.isin(self.icd_codes_cancer_meta),"Metastasis",
                              np.where(self.df_secondary_icd.icd_secondary_code.isin(self.icd_codes_cancer_meta_ln),"Metastasis LN",
                              np.where(self.df_secondary_icd.icd_secondary_code.isin(self.icd_codes_cancer),"Cancer",
                              np.where(self.df_secondary_icd.icd_secondary_code.isin(self.icd_codes_chronic),"Chronic",
                              "Acute")))))

           
    def load_procedures(self,
                        file_name : str,
                        col_names: dict | None = None ):
        
        self.df_procedures = pd.read_csv(self.path_data + file_name,sep=";")

        if col_names is not None : 
            self.df_procedures.rename(columns = col_names, inplace = True)

        self.df_procedures = self.df_procedures[~(self.df_procedures.procedure.isin(self.pathology_procedure))] 


    def get_names(self,
                  gender : int):

        first_name = self.df_names.prenom[(self.df_names.sexe==gender) & (self.df_names.prenom.str.len()>3)].sample(1).iloc[0]
        last_name = self.df_names.nom[ (self.df_names.nom.str.len()>3)].sample(1).iloc[0]

        return first_name[0].upper() + first_name[1:].lower() ,last_name[0].upper() + last_name[1:].lower()
    
    def sample_from_df(self,
                       profile : pd.Series ,
                       df_values : pd.DataFrame ,
                       nb : int | None = None,
                       col_weights : str = 'nb',
                       max_nb : int | None = 2 ,
                       distinct_chapter : bool = False,
                       ):

        """

        
        


        """

        query = ' & '.join(['{}=={}'.format(k, "'{}'".format(v) if isinstance(v, str) else v) for k, v in profile.items() if k in df_values.columns  ])

        df_sel = df_values.query(query)
        
        if(col_weights not in df_sel.columns):
            df_sel= df_sel.assign(col_weights = 1).rename(columns={"col_weights":col_weights})
        
        if df_sel[col_weights].sum() == 0:
            df_sel= df_sel.assign(col_weights = 1).rename(columns={"col_weights":col_weights})
        
        if df_sel.shape[0] ==0 :
            return pd.DataFrame(columns=df_values.columns)

        nb_sample_max = np.minimum(df_sel.shape[0],max_nb)


        #If nb is present, the number of samples if fixed and equal to the max possible.
        if nb is not None :
            nb_final_sample = np.minimum(df_sel.shape[0],nb)
        else:
            nb_final_sample = np.random.randint(nb_sample_max+1, size=1)[0]

        if nb_final_sample > 0:

            #Codes are from different chapter of ICD10
            # if distinct_chapter == True and "icd_secondary_code" in df_sample.columns:
            if distinct_chapter == True and "icd_secondary_code" in df_sel.columns:

                df_sample=None
                chapter = []

                for i in range(1,nb_final_sample+1):
                    df_sample=pd.concat([df_sample,df_sel[~(df_sel.icd_secondary_code.str.slice(0,1).isin(chapter))].sample(1, replace=False, weights = col_weights  )])
                    chapter = df_sample.icd_secondary_code.str.slice(0,1).to_list()
                    if len(df_sel[~(df_sel.icd_secondary_code.str.slice(0,1).isin(chapter))]) == 0:
                        break
           

            else:
                df_sample= df_sel.sample(nb_final_sample, replace=False, weights =col_weights)

            # Add description codes
            if  "icd_secondary_code" in df_sample.columns   :
                df_sample.drop_duplicates("icd_secondary_code",inplace=True)
                # df_sample["icd_code_description_alternative"] = df_sample.icd_secondary_code.apply(self.get_n_icd_alternative_descriptions)
                df_sample["icd_code_description_official"] = df_sample.icd_secondary_code.apply(self.get_icd_description)
                
                # return df_sample[["icd_secondary_code","icd_code_description_official","icd_code_description_alternative"]].reset_index(  drop=True  )
                return df_sample[["icd_secondary_code","icd_code_description_official"]].reset_index(  drop=True  )

            elif "procedure" in df_sample.columns  :
                
                df_sample["procedure_description_official"] = df_sample.procedure.apply(self.get_procedure_description)
                return df_sample
            else:
                return df_sample

        else:
            return pd.DataFrame(columns=df_values.columns)

    def get_clinical_scenario_template(self):
        return {
                'age': None,
                'sexe':None,
                'date_entry':None,
                'date_discharge': None,
                'date_of_birth':None,
                'first_name':None,
                'last_name':None,
                'icd_primary_code':None,
                # 'icd_primary_code_definition': None,
                # 'icd_primary_code_definition_alternatives': None,
                'case_management_type':None,
                'icd_secondary_code':[],
                'text_secondary_icd_official':"",
                'procedure':None,
                'icd_primary_description':None,
                'admission_mode':None,
                'discharge_disposition':None,
                'cancer_stage':None,
                'score_TNM':None,
                'histological_type':None,
                'treatment_recommandation':None,
                'chemotherapy_regimen':None,
                'biomarkers':None,
                'department' : None,
                'hospital':None,
                'first_name_med':None, 
                'last_name_med':None,
                'template_name': None
                
             
        }
        
    
    def get_n_icd_alternative_descriptions(self,
                    icd_code : str,
                    nb : int = 5):
        """
        Get synomym from ICD10 code
        
        """

        if icd_code in self.icd_codes_cancer_meta:
            icd_descriptions = self.df_icd_synonyms.icd_code_description[(self.df_icd_synonyms.icd_code==icd_code) & ( self.df_icd_synonyms.icd_code_description.str.contains("metastase"))]
        else:
            icd_descriptions = self.df_icd_synonyms.icd_code_description[self.df_icd_synonyms.icd_code==icd_code]

        #synonyms = df_icd_syn.dictionary_keys[df_icd_syn.code==code]
        if len(icd_descriptions) > 0 :
            nb_descrip = icd_descriptions.shape[0]
            nb_sample = np.minimum(nb_descrip,nb)
            string_descriptions = ", ".join(icd_descriptions.sample(nb_sample))
            return string_descriptions
        else:
            # Check if the code exists in the official ICD list
            official_description = self.df_icd_official.icd_code_description[self.df_icd_official.icd_code==icd_code]
            if len(official_description) > 0:
                return str(official_description.iloc[0])
            else:
                return "" # Return empty string if code not found in official list
    
    def get_icd_alternative_descriptions(self,
                    icd_code : str):
        """
        Get synomym from ICD10 code
        
        """

        if icd_code in self.icd_codes_cancer_meta:
            icd_descriptions = self.df_icd_synonyms.icd_code_description[(self.df_icd_synonyms.icd_code==icd_code) & ( self.df_icd_synonyms.icd_code_description.str.contains("metastase"))]
        else:
            icd_descriptions = self.df_icd_synonyms.icd_code_description[self.df_icd_synonyms.icd_code==icd_code]

        #synonyms = df_icd_syn.dictionary_keys[df_icd_syn.code==code]
        if len(icd_descriptions) > 0 :
            return str(icd_descriptions.sample(1).iloc[0])
        else:
            # Check if the code exists in the official ICD list
            official_description = self.df_icd_official.icd_code_description[self.df_icd_official.icd_code==icd_code]
            if len(official_description) > 0:
                return str(official_description.iloc[0])
            else:
                return "" # Return empty string if code not found in official list

    def get_icd_description(self,
                    icd_code : str):
        """
        Get official description from ICD10 code
        
        """

        official_description = self.df_icd_official.icd_code_description[self.df_icd_official.icd_code==icd_code]
        if len(official_description) > 0:
            return str(official_description.iloc[0])
        else:
            return "" # Return empty string if code not found in official list

    def get_procedure_description(self,
                    procedure : str):
        """
        Get official _description from procdure code
        
        """

        official__description = self.df_procedure_official.procedure_description[self.df_procedure_official.procedure==procedure].iloc[0]
        if len(official__description) > 0:
            return str(official__description)
        else:
            return "" # Return empty string if code not found in official list

    def define_text_managment_type(self,case):
        """
        The care management approach is a concept developed within the project to incorporate
        the hospitalization typology established by the ATIH within the framework of rules
        defining the ICD-10 diagnostic hierarchy. 

        Given the content of the clinical case the function will define :
        - The coding rule from ATIH rules defining the ICD-10 diagnostic hierarchy
        - A text that will be given to the model to describe precisely the context of the hospitalisation
        - The template of the document that will be generated

        """

        #The clinical situation in a text format that will be add to the final prompt
        situa = ""
        #The coding rule
        coding_rule = ""
        #The name of the user prompte template file (see description of the different possible files in the doc)
        template_name = "medical_inpatient.txt"

        regK = re.compile(r'K|k')
        #Identifyer of c section for obstetric
        csection = np.where(case["drg_parent_code"] in self.drg_parents_groups_csection,1,0)

        # Text for hospitalisation type and suffix used for template choices
        if case["admission_type"]  == "Outpatient" :
            text_admission_type = " en hospitalisation ambulatoire"
            ind_template = "out"
        else: 
            text_admission_type = "en hospialisation complète"
            ind_template = "in"

        # Suffix onco used in some situations
        if case["icd_primary_code"] in self.icd_codes_cancer:
            ind_template_onco= "_onco"
        else:
            ind_template_onco=""


        # FIRST : SIMPLE CASES where situations do not dependant on the primary diagnosis   
        # ---------------------------------------------------------------------------------
         
        # Special treatment for some cancer where all the scenario is come from treatment recommandation
        if case["histological_type"] is not None and case["drg_parent_code"][2:3] not in ["C","K"]:
            situa = "Hospitalisation pour prise en charge du cancer"
            coding_rule="other"


        # Règle D3-1 : hopistalisation pour exploration nocturne ou apparentée telle
        elif case["case_management_type"] in self.icd_codes_overnight_study:
            coding_rule="D3-1"
            # Règle D3-2 : hopistalisation pour  tests allergologiques
            template_name = "medical_outpatient.txt"
            situa =  "Prise en charge pour exploration nocturne ou apparentée telle"

        # Règle D3-2 : séjour programmé pour test allergologiques        
        elif case["case_management_type"] in self.icd_codes_sensitization_tests:
            coding_rule="D3-2"
            template_name = "medical_outpatient.txt"
            situa =  "Prise en charge en hospitalistion de jour pour réalisation de test de réactivité allergiques"
        
        # Règle T1 : Traitement répétifs transfusions        
        elif case["drg_parent_code"] in self.drg_parent_code_transfusion :
            coding_rule = "T1"
            situa = "Prise en charge pour " + case["drg_parent_description"].lower()
            template_name = "medical_outpatient.txt"
        
        # Règle T1 : Traitement répétifs aphérèse    
        elif case["drg_parent_code"] in self.drg_parent_code_apheresis :
            coding_rule = "T1"
            situa = "Prise en charge pour " + case["drg_parent_description"].lower()
            template_name = "medical_outpatient.txt"

        # Règle T1 : Traitement répétifs dialyse : pour l'instant exlcus 
        # Règle T1 : Traitement répétifs chimio cf

        # Règle T2 : Exceptions à T1 (douleur chronique, ascite, épanchement pleural, toxine botulique)
        elif case["icd_primary_code"] in self.icd_codes_ascites:
            coding_rule = "T2-R18"  
            situa =  "Prise en charge pour ponction d'ascite  " + text_admission_type
            template_name = "medical_"+ ind_template +"patient.txt"
        
        # Règle T2 : Exceptions à T1 (douleur chronique, ascite, épanchement pleural, toxine botulique)        
        elif case["icd_primary_code"] in self.icd_codes_pleural_effusion:
            coding_rule = "T2-J9"  
            situa =  "Prise en charge pour ponction pleurale "+ text_admission_type
            template_name = "medical_"+ ind_template +"patient.txt"

        
        # Règle T2 : Exceptions à T1 (douleur chronique, ascite, épanchement pleural, toxine botulique)
        elif case["procedure"]  in self.procedure_botulic_toxin and case["admission_type"]  == "Outpatient" :
            coding_rule  = "T2-Toxine"  
            situa =  "Prise en charge en hospitalisation ambulatoire pour injection de toxine botulique"
            template_name = "medical_"+ ind_template +"patient.txt"
        
        # Règle T2 : Exceptions à T1 (douleur chronique, ascite, épanchement pleural, toxine botulique)
        elif case["icd_primary_code"]  in self.icd_codes_t2_chronic_intractable_pain:
            coding_rule = "T2-R52"  
            situa =  "Prise en charge d'une douleur chronique rebelle " + text_admission_type
            template_name = "medical_"+ ind_template +"patient.txt"
                                   

        # Règle T3 : Traitement unique chirurgical
        elif case["drg_parent_code"][2:3] == "C" and case["drg_parent_code"] not in self.drg_parents_groups_delivery :
            coding_rule = "T3"
            situa = "Prise en charge "+ text_admission_type  + " pour "+ case["drg_parent_description"].lower()
            template_name = "surgery_"+ ind_template +"patient.txt"


        # Règle T4 : Cosmetic surgery     
        elif case["case_management_type"] in self.icd_codes_cosmetic_surgery:
            coding_rule = "T4"
            situa =  "Prise en charge "+text_admission_type + " pour " + case["text_procedure"].lower()
            template_name = "surgery_"+ ind_template +"patient.txt"
            
 
        # Règle T5 : Chirurgie plastique non esthétique
        elif case["case_management_type"] in self.icd_codes_plastic_surgery:
            coding_rule ="T5"
            situa =  "Prise en charge "+text_admission_type + " pour " + case["text_procedure"].lower()
            template_name = "surgery_"+ ind_template +"patient.txt"


        # Règle T6 : Intervention de confort
        elif case["case_management_type"] in self.icd_codes_comfort_intervention:
            coding_rule = "T6"
            situa =  "Prise en charge "+ text_admission_type + " pour " + case["text_procedure"].lower()
            template_name = "surgery_"+ ind_template +"patient.txt"
        
        # Règle T7 : soins de stomies 
        elif case["drg_parent_code"] in self.drg_parent_code_stomies:
            coding_rule ="T7"
            situa = "Prise en charge "+ text_admission_type  + " pour "+ case["drg_parent_description"].lower()
            template_name = "medical_"+ ind_template +"patient.txt"


        # Règle T8 : réalisation d'acte thérapeutique par voie endoscopique, endovasculaire ou d'imagerie interventionnelle,
        elif case["icd_primary_code"] =="C186":# case["drg_parent_code"][2:3] == "K" :
            coding_rule = "T8"
            situa = "Prise en charge "+ text_admission_type  + " pour "+ case["drg_parent_description"].lower()
            template_name = "medical_"+ ind_template +"patient.txt"


           
        # Règle T11 : Soins palliatifs
        elif case["drg_parent_code"] in self.drg_parent_code_palliative_care : 
            coding_rule ="T11"
            situa = "Prise en charge "+ text_admission_type  + " pour soins palliatifs"
            template_name = "medical_"+ ind_template +"patient.txt"
        
            
            
        # Règle IVG : interuption volontaire de grossesse
        elif case["case_management_type"] in self.icd_codes_legal_abortion:
            coding_rule = "Legal_Abortion"
            situa =  "Prise en charge pour interruption volontaire de grossesse"
            template_name = "medical_"+ ind_template +"patient.txt"
            
       
        # Règle IMG :interruption médicale de grossesse
        elif case["case_management_type"] in self.icd_codes_medical_abortion:
            coding_rule = "Medical_Abortion"
            situa =  "Prise en charge pour interruption médicale de grossesse"
            template_name = "medical_"+ ind_template +"patient.txt"

        # Règle T12: Accouchements
        elif case["drg_parent_code"] in self.drg_parents_groups_delivery:
            coding_rule = "T12"
            
            # 85% through emergecies (normal) , 15% preceded by and admission in hopsitalisation
            option_delivery = np.random.choice(2, p=[0.85, 0.15])
            if option_delivery==1:
                suffix_temp_delivery = "_urg"
            else:
                suffix_temp_delivery = "_hospit"
            
            # Csection
            if case["procedure"] in self.procedure_csection :
                situa =  "Prise en charge pour accouchement par césarienne"
                template_name = "delivery_inpatient_csection"+ suffix_temp_delivery +".txt"
                
            else :
                situa =  "Prise en charge pour accouchement par voie basse"
                template_name = "delivery_inpatient"+ suffix_temp_delivery +".txt"

        elif (case["drg_parent_code"] in self.drg_parent_code_deceased) | (case["discharge_disposition"] == "DECES"):
            situa =  "Hospitalisation au cours de laquelle le patient est décédé"
            code = 10
        #TODO : others cases of supervision 
        
 


        # SECOND : Situations where we need to take into account primary icd code   
        # ---------------------------------------------------------------------------------

        # - cancer
        #   * Hospital admission with initial diagnosis of the cancer 
        #   * Hospital admission for cancer workup
        #   * Hospital admission for initiation of treatment
        #   * Hospital admission for relapse or recurrence of the cancer
        #   * repeated treatment : chimio, radotherapy
        elif case["icd_primary_code"] in self.icd_codes_chronic :
            
            #  Règle T1 traitement répétitifs chimio
            if case["drg_parent_code"] in self.drg_parent_code_chimio :
                coding_rule = "T1"
                situa = "Prise en charge "+ text_admission_type +"pour cure de chimiothérapie"
                template_name = "medical_"+ ind_template +"patient_onco.txt"


                if case["chemotherapy_regimen"] is not None and not (isinstance(case["chemotherapy_regimen"], float)):
                    situa += ". Le protocole actuellement suivi est : "+ case["chemotherapy_regimen"]
            
            #  Règle T1 traitement répétitifs chimio
            if case["case_management_type"] in ["Z512"]:
                coding_rule = "T1"
                situa = "Prise en charge "+ text_admission_type +"pour administration d'un traitement médicamenteux nécessitant une hospitalisation"
                template_name = "medical_"+ ind_template +"patient.txt"

            #  Règle T1 traitement répétitifs radiothérapie
            elif case["drg_parent_code"] in self.drg_parent_code_radio :
                coding_rule = "T1"
                situa = "Prise en charge "+ text_admission_type +" pour réalisation du traitement par radiothérapie"
                template_name = "medical_"+ ind_template +"patient_onco.txt"
            
            #  Rules D1,D5,D9 cases where chronic disease is the icd primary diagnosis
            elif case["case_management_type"] =="DP" :
                option = np.random.choice(4, p=[0.4, 0.2,0.2,0.2])
                if option == 0:
                        coding_rule = "D1"
                        situa = "Première hospitalisation "  + text_admission_type + " pour découverte de " + case["icd_primary_description"] # 40%
                        template_name = "medical_"+ ind_template +"patient"+ind_template_onco+".txt"

                elif option == 1:
                        coding_rule = "D9"
                        situa = "Hospitalisation "+ text_admission_type +" pour bilan initial pré-trérapeutique de " + case["icd_primary_description"] # 20%
                        template_name = "medical_"+ ind_template +"patient"+ind_template_onco+".txt"
                
                elif option == 1:
                        coding_rule = "D9"
                        situa = "Hospitalisation "+ text_admission_type +" pour mise en route du traitement de " + case["icd_primary_description"] # 20%
                        template_name = "medical_"+ ind_template +"patient"+ind_template_onco+".txt"
                else:
                    if case["icd_primary_code"] in self.icd_codes_cancer:
                        coding_rule = "D5"
                        situa = "Hospitalisation "+ text_admission_type +" pour rechutte après traitement de  " + case["icd_primary_description"] # 20%
                        template_name = "medical_"+ ind_template +"patient"+ind_template_onco+".txt"

                    elif case["icd_primary_code"] in self.icd_codes_diabetes_chronic:
                        coding_rule = "D5"
                        situa = "Hospitalisation "+ text_admission_type +" pour changement de stratégie thérapeutique  " + case["icd_primary_description"] # 20%
                        template_name = "medical_"+ ind_template +"patient"+ind_template_onco+".txt"                  
                    
                    elif case["icd_primary_code"][0:3] not in ["E05","J45","K85"] :
                        coding_rule = "D5"
                        situa = "Hospitalisation "+ text_admission_type +" pour poussée aigue de la maladie  " + case["icd_primary_description"] # 20%
                        template_name = "medical_"+ ind_template +"patient"+ind_template_onco+".txt"  
            
            #  Rules S1-Chronic supervision of chronical diseases
            elif  case["case_management_type"] in self.icd_codes_supervision_chronic_disease :
                        coding_rule = "S1-Chronic"
                        situa = "Surveillance "+ text_admission_type +" de " + case["icd_primary_description"] 
                        template_name = "medical_"+ ind_template +"patient"+ind_template_onco+".txt"                     
           
        # Medical acute pathologies 
        else :

         
            if case["case_management_type"]  == "DP":
                situa =  "Pour prise en charge diagnostique et thérapeutique du diagnotic principal " + text_admission_type
                

                # print(code)
            else:
                situa =  "Pour prise en charge " + text_admission_type + " pour " + case["case_management_type_description"]

                # print(code)
            coding_rule = "other"
            template_name = "medical_"+ ind_template +"patient"+ind_template_onco+".txt"

        return (situa, coding_rule,template_name)
            
        


   


    def generate_scenario_from_profile(self,
                                       profile,
                                       add_icd_secondary_code : int=0):
        
        profile["icd_parent_code"] = profile["icd_primary_code"][0:3]

        scenario = self.get_clinical_scenario_template()

        is_cancer = 0
        icd_secondary_profile = 0
        age_profile = 0
        los_profile= 0
        los_mean_profile = None
        los_sd_profile  = None
        los_profile = None
          
        for k,v in profile.items():
            scenario[k]=v
            #Cases were secondary diagnosis are in the profile
            if k=="icd_secondary_code":
                icd_secondary_profile = 1
            if k=="age2":
                age_profile = 1
            if k=="los":
                los_profile=profile.los
            if k=="los_mean":
                los_mean_profile=profile.los_mean
            if k=="os_sd":
                los_sd_profile=profile.os_sd      
        
        if isinstance(profile.sexe,str) :
                    profile.sexe = int(profile.sexe)           
       
        profile.year = random.sample(self.simulations_years,1)[0]
        
        ### Administratives elements
        if age_profile==0 : 
            scenario["age"] = get_age(profile.cage)
        else : 
            scenario["age"] = scenario["age2"]
        scenario["date_entry"],scenario["date_discharge"] = get_dates_of_stay(profile.admission_type,profile.admission_mode,los_mean_profile,los_sd_profile,los_profile,profile.year)
        scenario["date_of_birth"] = random_date_between( scenario["date_entry"] - datetime.timedelta(days = 365*(scenario["age"]+1)) , scenario["date_entry"] - datetime.timedelta(days = 365*(scenario["age"])))
        scenario["first_name"] , scenario["last_name"] = self.get_names(profile.sexe)
        scenario["first_name_med"] , scenario["last_name_med"] = self.get_names(random.randint(1, 2))

        scenario["departement"] = profile["specialty"]

        scenario["hospital"] =   self.df_hospitals.sample(1)['hospital'].iloc[0]
        
        
        ##Get additional informations for cancer case from treatment recommandation
        if scenario["icd_primary_code"] in self.icd_codes_cancer:
                is_cancer =1
        ## When care pathway is related to the treatment of cancer and when recommandations are availabe, the clinical case will be create from those recommandation
        if scenario["case_management_type"] in ['DP','Z511'] : 
                
            treatment_recommendations = self.sample_from_df(profile =profile,df_values= self.df_cancer_treatment_recommandation,nb=1) 
            if treatment_recommendations.shape[0]>0 :
                scenario["histological_type"] = treatment_recommendations["histological_type"].iloc[0] 
            
                score_TNM = treatment_recommendations["TNM"].iloc[0]
                if score_TNM not in ['Variable','Non pertinent'] :
                    scenario["score_TNM"] = score_TNM
            
                stage = treatment_recommendations["stage"].iloc[0]
                if stage not in ['Variable','Non pertinent'] :
                    scenario["cancer_stage"] = stage
                
                scenario["treatment_recommandation"] = treatment_recommendations["treatment_recommandation"].iloc[0] 
                if treatment_recommendations.chemotherapy_regimen.notna().bool:
                    scenario["chemotherapy_regimen"] = treatment_recommendations["chemotherapy_regimen"].iloc[0]  

                scenario["biomarkers"] = treatment_recommendations["biomarkers"].iloc[0]
            
            



        ### Principals diagnosis
        scenario["icd_primary_description"] = self.get_icd_description(profile.icd_primary_code)

        # scenario["icd_primary_description_alternative"] = self.get_icd_alternative_descriptions(profile.icd_primary_code)
        scenario["case_management_type_description"] = self.get_icd_description(profile.case_management_type)

        if icd_secondary_profile==1:
            if len(scenario["icd_secondary_code"])>0:
                for code in scenario["icd_secondary_code"]:    
                    scenario["text_secondary_icd_official"] += "- " + self.get_icd_description(code) + " ("+ code +")\n"
        
        if add_icd_secondary_code==1:
            ### Secondary diagnosis :
            ### We sample secondary diagnosis by steps : metastases, metastases ln, chronic,complications
            ### Each time build :
            ### - official descriptions
            ### - official : alternatives descripttion
            scenario["text_secondary_icd_official"]=""
            # scenario["text_secondary_icd_alternative"]=""

            grouping_secondary =["icd_primary_code","icd_secondary_code","cage2","sexe","nb"] 

            ### Scenarios will be much more different when clinical case is about cancer
            ### Attribute DAS to each situations

            #Function to attribute secondary icd diagnosis for each key (sexe,new_cage,categ_cim):
            #- Metastase :
            #* choose randomly if patient has a metastase regarding metastasis distribution
            #* choose randomly the number of metastasis in df_das_new_meta_n_distinct
            #* choose randomly the metastic codes in df_das_new_meta regarding distribution of case (nb_das)
            #- Chronic disease :
            #* choose randomly the number of chronic disease in regard with df_das_new_chronic_n_distinct taking into account a zero option
            #* choose randomly the list of chronic disease in the df_das_new_chronic dataset regarding distribution of case (nb_das)
            #- Complication :
            #* choose randomly the number of complications in regard with df_das_new_complication_n_distinct taking into account a zero option
            #* choose randomly the list of complications in the df_das_new_complication dataset regarding distribution of case (nb_das)

 
            ### Categories of chronic desease : when cancer you don't sample chronic diseases over cancer icd codes

            if is_cancer ==1 :
                chronic_diseases = self.sample_from_df(profile =profile,df_values= self.df_secondary_icd.query("type.isin(['Chronic'])")[grouping_secondary], distinct_chapter=True)

            else :     
                # chronic_diseases =  self.sample_from_df(profile =profile,df_values= self.df_secondary_icd.query("type.isin(['Chronic'])")[grouping_secondary]) 
                df_values = self.df_secondary_icd.query("type.isin(['Chronic','Cancer'])")[grouping_secondary]
                #df_secondary_cancer = self.df_secondary_icd[self.df_secondary_icd.icd_secondary_code.isin(self.icd_codes_cancer)][grouping_secondary]
                
                #df_values = pd.concat([df_values, df_secondary_cancer])
                chronic_diseases =  self.sample_from_df(profile =profile,df_values=df_values, distinct_chapter=True)  

            if chronic_diseases.shape[0] > 0 :
                for index, row in chronic_diseases.iterrows():
                    scenario["text_secondary_icd_official"] += "- " + row.icd_code_description_official + " ("+ row.icd_secondary_code+")\n"
                    # scenario["text_secondary_icd_alternative"] += "- " + row.icd_code_description_official + "("+ row.icd_secondary_code+") : " + row.icd_code_description_alternative + "\n"
                
                scenario["icd_secondary_code"] = chronic_diseases.icd_secondary_code.to_list()

            ### Is we sampled cancer codes in the chronic disease we will also sample metastasis
            if len(scenario["icd_secondary_code"])>0 :
                if bool(set(scenario["icd_secondary_code"]) & set(self.icd_codes_cancer)) :
                    is_cancer = 1
                

            ### LN metastasis
            if is_cancer ==1 :

                ##If TNM is know sample metastasis regarding this status
                if scenario["score_TNM"] is not None and not (isinstance(scenario["score_TNM"], float)):
                    if bool(re.search("N[123x+]",scenario["score_TNM"])) :
                        metastases_ln = self.sample_from_df(profile =profile,df_values= self.df_secondary_icd.query("type=='Metastasis LN'")[grouping_secondary],nb = 1)  
                
                        if metastases_ln.shape[0] > 0 :
                            for index, row in metastases_ln.iterrows():
                                scenario["text_secondary_icd_official"] += "- " + row.icd_code_description_official + " ("+ row.icd_secondary_code+")\n"
                                # scenario["text_secondary_icd_alternative"] += "- " + row.icd_code_description_official + "("+ row.icd_secondary_code+") : " + row.icd_code_description_alternative + "\n"

                            scenario["icd_secondary_code"] = scenario["icd_secondary_code"] + metastases_ln.icd_secondary_code.to_list()

                    if bool(re.search("M[123x+]",scenario["score_TNM"])) :
                        metastases = self.sample_from_df(profile =profile,df_values= self.df_secondary_icd.query("type=='Metastasis'")[grouping_secondary])  
                
                        if metastases.shape[0] > 0 :
                                for index, row in metastases.iterrows():
                                    scenario["text_secondary_icd_official"] += "- " + row.icd_code_description_official + " ("+ row.icd_secondary_code+")\n"
                                    # scenario["text_secondary_icd_alternative"] += "- " + row.icd_code_description_official + "("+ row.icd_secondary_code+") : " + row.icd_code_description_alternative + "\n"

                                scenario["icd_secondary_code"] = scenario["icd_secondary_code"] + metastases.icd_secondary_code.to_list()
                        
                
                #When TNM is not known, sample metastasis among all possible situations
                else:
                    metastases = self.sample_from_df(profile =profile,df_values= self.df_secondary_icd.query("type.isin(['Metastasis','Metastasis LN'])")[grouping_secondary])  
                
                    if metastases.shape[0] > 0 :
                        for index, row in metastases.iterrows():
                            scenario["text_secondary_icd_official"] += "- " + row.icd_code_description_official + " ("+ row.icd_secondary_code+")\n"
                            # scenario["text_secondary_icd_alternative"] += "- " + row.icd_code_description_official + "("+ row.icd_secondary_code+") : " + row.icd_code_description_alternative + "\n"
                            
                        scenario["icd_secondary_code"] = scenario["icd_secondary_code"] + metastases.icd_secondary_code.to_list()

            #For complication drg_parent_code we choose grouping profile only on ICD
            grouping_secondary =["drg_parent_code","icd_secondary_code","cage2","sexe","nb"]

            complications = self.sample_from_df(profile =profile,df_values= self.df_secondary_icd.query("type.isin(['Acute'])")[grouping_secondary]) 

            if complications.shape[0] > 0 :
                for index, row in complications.iterrows():
                    scenario["text_secondary_icd_official"] += "- " + row.icd_code_description_official + " ("+ row.icd_secondary_code+")\n"
                    # scenario["text_secondary_icd_alternative"] += "- " + row.icd_code_description_official + "("+ row.icd_secondary_code+") : " + row.icd_code_description_alternative + "\n"
                
            scenario["icd_secondary_code"] = scenario["icd_secondary_code"] + complications.icd_secondary_code.to_list()

        ## Actes

        grouping_procedure =["procedure","drg_parent_code","icd_primary_code","cage2","sexe"]
        procedures = self.sample_from_df(profile =profile,df_values= self.df_procedures[grouping_procedure],nb=1) 

        if len(procedures) > 0 :
            scenario["procedure"] = procedures.procedure.values[0]
            scenario["text_procedure"] =procedures.procedure_description_official.values[0]
        else:
            scenario["procedure"] = ""
            scenario["text_procedure"] ="" 

        #for index, row in procedures.iterrows():
        #        scenario["text_procedure"] = row.procedure_description_official
        #        scenario["procedure"] = row.procedure


        scenario["case_management_type_text"] , scenario["coding_rule"],  scenario["template_name"] = self.define_text_managment_type(scenario)

        if scenario["coding_rule"] in self.coding_rules :
            scenario["case_management_description"] = self.coding_rules[scenario["coding_rule"]]['texte']
        else:
            scenario["case_management_description"] =""
        

        return scenario



    def make_prompts_marks_from_scenario(self,
                                        scenario):

        SCENARIO = "**SCÉNARIO DE DÉPART :**\n"

        for k,v in scenario.items():
            if k == "age" and v is not None:
                SCENARIO +="- Âge du patient : " + str(v) + " ans\n"
           
            if k == "sexe" and v is not None:  
                SCENARIO +="- Sexe du patient : " + interpret_sexe(v) + "\n"
            
            if k == "date_entry" and v is not None:  
                SCENARIO +="- Date d'entrée : "+ v.strftime("%d/%m/%Y") + "\n"
            
            if k == "date_discharge" and v is not None:  
                SCENARIO +="- Date de sortie : "+ v.strftime("%d/%m/%Y") + "\n" 
            
            if k == "date_of_birth" and v is not None:  
                SCENARIO +="- Date de naissance : "+ v.strftime("%d/%m/%Y") + "\n"  
            
            if k == "last_name" and v is not None:  
                SCENARIO +="- Nom du patient : "+ v + "\n" 
            
            if k == "first_name" and v is not None:  
                SCENARIO +="- Prénom du patient : "+ v + "\n" 
                
            if scenario["icd_primary_code"] in self.icd_codes_cancer: 
                if k == "icd_primary_description" and v is not None:  
                    SCENARIO +="- Localisation anatomique de la tumeur primaire : "+ v + " (" + scenario["icd_primary_code"] + ")\n" 
                if k == "histological_type":
                    if v is not None and not (isinstance(v, float)):  
                        SCENARIO +="- Type anatomopathologique de la tumeur primaire : "+ v + "\n" 
                    else :
                        SCENARIO +="- Type anatomopathologique de la tumeur primaire : Vous choisirez vous même un type histologique cohérent avec la localisation anatomique\n" 
                if k == "score_TNM":
                    if v is not None and not (isinstance(v, float)):   
                        SCENARIO +="- Score TNM : "+ v + "\n" 
                    else :
                        SCENARIO +="- Score TNM : Si la notion de score de TNM est pertinente avec le type histologique et la localisation anatomique, vous choisirez un score TNM\n" 
                if k == "cancer_stage":
                    if v is not None and not (isinstance(v, float)):   
                        SCENARIO +="- Stade tumoral : " + v + "\n" 
                if k == "biomarkers":
                    if v is not None and not (isinstance(v, float)):   
                        SCENARIO +="- Biomarqueurs tumoraux : "+ v + "\n" 
                    else :
                        SCENARIO +="- Biomarqueurs tumoraux : Vous choisirez des biomarqueurs tumoraux cohérents avec la localisation anatomique et l'histologie de la tumeur\n" 
            
            if k == "admission_mode" and v is not None:  
                SCENARIO +="- Mode d'entrée' : "+ v + "\n" 
           
            if k == "discharge_disposition" and v is not None:  
                SCENARIO +="- Mode de sortie' : "+ v + "\n" 

            if k == "case_management_type" and v is not None:  
                SCENARIO +="- Contexte de l'hospitalisation : "+ scenario["case_management_type_text"] +". " +scenario["case_management_description"] + "\n"

                SCENARIO +="- Codage CIM10 :\n" 
                #if scenario["case_management_type"]!="DP":
                #    SCENARIO +="   * Code CIM prise en charge :\n"  +  scenario["case_management_type_description"] + " ("+ scenario["case_management_type"] + ")\n"  
               
                SCENARIO +="   * Diagnostic principal : "+  scenario["icd_primary_description"] + " ("+ scenario["icd_primary_code"] + ")\n"          
                               
                SCENARIO +="   * Diagnostic associés : \n"
                SCENARIO +=  scenario["text_secondary_icd_official"]  + "\n" 
            
            if k == "procedure" and v is not None and scenario["drg_parent_code"][2:3] in ["C","K"] : 
                SCENARIO +=  "* Acte CCAM :\n" + scenario["text_procedure"].lower()+ "\n"  
            
            if k == "first_name_med" and v is not None:  
                SCENARIO +="- Nom du médecin / signataire : "+ v + " " + scenario["last_name_med"] + "\n" 
            
            if k == "specialty" and v is not None and not (isinstance(v, float)):  
                SCENARIO +="- Service : "+ v + "\n" 
            
            if k == "hospital" and v is not None and not (isinstance(v, float)):  
                SCENARIO +="- Hôpital : "+ v + "\n" 
        # ICD_ALTERNATIVES =""


        #ICD_ALTERNATIVES +=" - " + scenario["icd_primary_description"] + "("+ scenario["icd_primary_code"] + ") : " 
        #ICD_ALTERNATIVES +=": "+ scenario["icd_primary_description_alternative"] + "\n"
        #ICD_ALTERNATIVES +=  scenario["text_secondary_icd_alternative"]  + "\n"  

        
        # INSTRUCTIONS_CANCER
        if scenario["icd_primary_code"] in self.icd_codes_cancer: 
            SCENARIO += "Ce cas clinique concerne un patient présentant un cancer\n"
            if scenario["histological_type"] is not None:
                SCENARIO +="Vous choisirez un épisode de traitement sachant que les recommandations pour ce stade du cancer sont les suivantes :\n"
                SCENARIO +="   - Schéma thérapeutique : " + scenario["treatment_recommandation"] + "\n"
                if scenario["chemotherapy_regimen"] is not None and not (isinstance(scenario["chemotherapy_regimen"], float)): 
                    SCENARIO += "   - Protocole de chimiothérapie : " + scenario["chemotherapy_regimen"]  + "\n"
            

            SCENARIO += "Veillez à bien préciser le type histologique et la valeur des biomarqueurs si recherchés\n"

        # return {"SCENARIO": SCENARIO, "ICD_ALTERNATIVES" : ICD_ALTERNATIVES, "INSTRUCTIONS_CANCER":INSTRUCTIONS_CANCER}
        return SCENARIO

    def create_system_prompt(self,scenario):
        if scenario["icd_primary_code"] in self.icd_codes_cancer: 
            if scenario['admission_type'] == "Inpatient" and scenario['drg_parent_code'][2:3]=="C" :
                template_name = "surgery_inpatient_onco.txt"
            elif scenario['admission_type'] == "Outpatient" and scenario['drg_parent_code'][2:3]=="C" :
                template_name = "surgery_outpatient_onco.txt"
            elif scenario['admission_type'] == "Outpatient" :
                template_name = "medical_outpatient_onco.txt"
            else:
                template_name = "medical_inpatient_onco.txt"
        
        else:
            if scenario['admission_type'] == "Inpatient" and scenario['drg_parent_code'][2:3]=="C" :
                template_name = "surgery_inpatient.txt"
            elif scenario['admission_type'] == "Outpatient" and scenario['drg_parent_code'][2:3]=="C" :
                template_name = "surgery_outpatient.txt"
            elif scenario['admission_type'] == "Outpatient" :
                template_name = "medical_outpatient.txt" 
            else:
                template_name = "medical_inpatient.txt"            
            
        with open("templates/" + scenario['template_name'], "r", encoding="utf-8") as f:
            prompt = f.read()
        
        return prompt


####-----------------------------------------------------------------------------------------------------------------------------
#### GENERATION WITH MISTRAL API
import argparse
import json
import os
import random
import time
from io import BytesIO

import httpx
from mistralai import File, Mistral

def create_client():
    """
    Create a Mistral client using the API key from environment variables.

    Returns:
        Mistral: An instance of the Mistral client.
    """
    return Mistral(api_key=os.environ["MISTRAL_API_KEY"])

def generate_random_string(start, end):
    """
    Generate a random string of variable length.

    Args:
        start (int): Minimum length of the string.
        end (int): Maximum length of the string.

    Returns:
        str: A randomly generated string.
    """
    length = random.randrange(start, end)
    return ' '.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=length))

def print_stats(batch_job):
    """
    Print the statistics of the batch job.

    Args:
        batch_job: The batch job object containing job statistics.
    """
    print(f"Total requests: {batch_job.total_requests}")
    print(f"Failed requests: {batch_job.failed_requests}")
    print(f"Successful requests: {batch_job.succeeded_requests}")
    print(
        f"Percent done: {round((batch_job.succeeded_requests + batch_job.failed_requests) / batch_job.total_requests, 4) * 100}")


def create_input_file(client, data):
    """
    Create an input file for the batch job.

    Args:
        client (Mistral): The Mistral client instance.
        num_samples (int): Number of samples to generate.

    Returns:
        File: The uploaded input file object.
    """
    buffer = BytesIO()
    for idx in range(len(data)):
        request = {
            "custom_id": str(idx),
            "body": {
                "max_tokens":  128_000,
                "messages":  [
                    {
                        "role": "system",
                        "content": data.iloc[idx]["system_prompt"]
                        },
                    {
                        "role": "user",
                        "content": data.iloc[idx]["user_prompt"]
                        },
                    {
                        "role": "assistant",
                        "content": data.iloc[idx]["prefix"],
                        "prefix": True
                        },
                    ]
            }
        }
        buffer.write(json.dumps(request).encode("utf-8"))
        buffer.write("\n".encode("utf-8"))
    return client.files.upload(file=File(file_name="file.jsonl", content=buffer.getvalue()), purpose="batch")


def run_batch_job(client, input_file, model):
    """
    Run a batch job using the provided input file and model.

    Args:
        client (Mistral): The Mistral client instance.
        input_file (File): The input file object.
        model (str): The model to use for the batch job.

    Returns:
        BatchJob: The completed batch job object.
    """
    batch_job = client.batch.jobs.create(
        input_files=[input_file.id],
        model=model,
        endpoint="/v1/chat/completions",
        metadata={"job_type": "testing"}
    )

    while batch_job.status in ["QUEUED", "RUNNING"]:
        batch_job = client.batch.jobs.get(job_id=batch_job.id)
        #print_stats(batch_job)
        time.sleep(1)

    print(f"Batch job {batch_job.id} completed with status: {batch_job.status}")
    return batch_job


def download_file(client, file_id, output_path):
    """
    Download a file from the Mistral server.

    Args:
        client (Mistral): The Mistral client instance.
        file_id (str): The ID of the file to download.
        output_path (str): The path where the file will be saved.
    """
    if file_id is not None:
        print(f"Downloading file to {output_path}")
        output_file = client.files.download(file_id=file_id)
        with open(output_path, "wb") as f:
            for chunk in output_file.stream:
                f.write(chunk)
        print(f"Downloaded file to {output_path}")

def extract_json(text):
  match = re.search(r"```json(.*?)```", text, re.DOTALL)
  if match:
    return match.group(1).strip()
  else:
    return None

def clean_bold(text):
  return re.sub(r"\*\*(.*?)\*\*", r"\1", text)

def clean_header(text):
  clean_text = re.sub(r'^##+ .*$', '', text, flags=re.MULTILINE)
  clean_text = re.sub(r'^--+$', '', clean_text, flags=re.MULTILINE)
  return clean_text

def fix_multiline_strings(json_text):
  """
  There are a few CRs (values of the "CR" key of the dictionary) that contain new lines in bad formats, which make `json.loads` fail.
  This function aims to fix them.
  """
  def replacer(match):
    content = match.group(1)
    content = (content
               .replace('"', '\\"')
               .replace('\\\\"', '\\"')
               .replace("\n", "\\n"))
    formulation_wording = match.group(2)
    return f'"CR": "{content}"{formulation_wording}'

  fixed = re.sub(r'"CR":\s*"(.*?)"(,\s*"formulations")', replacer, json_text, flags=re.DOTALL)
  return fixed

def delete_comments(json_text):
  """
  There are a few annotations (values of the "formulations" key of the dictionary) that contain comments of the format: // or /* */, which make `json.loads` fail.
  This function aims to fix them.
  """
  json_text = re.sub(r'//.*', '', json_text)
  json_text = re.sub(r'/\*.*?(?:\*/|\n)', '', json_text, flags=re.DOTALL)
  return json_text

def extract_generations_annotations(response):

  response = extract_json(response)
  if response ==None :
    return (None, None, None)

  response = fix_multiline_strings(response)
  response = delete_comments(response)
  try:
    response_dict = json.loads(response)
  except json.JSONDecodeError:
    return (None, None, None)

  if isinstance(response_dict, dict):
    if ("CR" in response_dict) and ("formulations" in response_dict):
      if isinstance(response_dict["formulations"], dict):
        if ("diagnostics" in response_dict["formulations"]) and ("informations" in response_dict["formulations"]):
          return (clean_bold(clean_header(response_dict["CR"])).strip(), response_dict["formulations"]["diagnostics"], response_dict["formulations"]["informations"])
        else:
          return (None, None, None)
      else:
        return (None, None, None)
    else:
      return (None, None, None)
  else:
    return (None, None, None)

def get_icd_coding_target(case) : 

    case_management_type = case.case_management_type
    case_management_type_description = case.case_management_type_description
    diagnosis = case.response_diagnosis

    #Regular expressions 

    PCID = "- Diagnostic principal : \n"
    SICD = "- Diagnotics associés : \n"
    CMT = "- Motif de recours au soin (code en Z du chapitre XXI): \n"

    if case_management_type == "DP":
        CMT+= "* Aucun\n"
    else :
        CMT+= "* " + case_management_type_description + "(" + case_management_type + ")\n"
    icd_primary_pred = ""
    icd_secondary_pred = []
    icd_coding_list  = []

    
    for k,v in diagnosis.items():
        text_code = k
        code_list =  re.findall(r'\(([A-Z]\d{2,5}\+?\d*)\)', k)
        code = code_list[0] if code_list else ""

        if(len(code)==0):
            code_list = re.findall(r'[A-Z]\d{2,5}\+?\d*', k)
            code = code_list[0] if code_list else ""
            description_list = re.findall(r'[A-Z][a-z].*',k)
            description = description_list[0] if description_list else ""
            text_code = description + '('+ code +')'
        
        if  re.findall(code,case.icd_primary_code) :
                PCID += "* " + text_code +" - " +   ",".join(v) + "\n"
                icd_primary_pred = code
                icd_coding_list+= [code]
        else :
                SICD += "* " + text_code +" - " +   ",".join(v) + "\n"
                icd_secondary_pred += [code]
                icd_coding_list+= [code]
                
    return icd_primary_pred,icd_secondary_pred, PCID+SICD+CMT,icd_coding_list


def prepare_training_files(path_results,job_name,nb_examples = None):

    df_res_final = pd.DataFrame()
    j = 0

    json_files = [f for f in listdir(path_results + job_name) if isfile(os.path.join(path_results + job_name, f)) and 'json' in f and 'batch' in f]

    for file_name in json_files :
        file_path = os.path.join(path_results + job_name ,file_name )
        i = int(re.findall(r'\d+',file_name)[0])
        if os.path.exists(file_path):
            results = []
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    results.append(json.loads(line.strip()))
                    j+=1
                    if nb_examples is not None:
                        if j> nb_examples:
                            break
            
            prep_dict=[]
            
            for result_item in results:
                    # Check if the item has a response and extract it
                    if "response" in result_item and result_item["response"] and "body" in result_item["response"] and "choices" in result_item["response"]["body"]:
                        response = result_item["response"]["body"]["choices"][0]["message"]["content"]
                        clinical_report,response_diagnosis,response_structured_data = extract_generations_annotations(response)
                        prep_dict.append({"bacth":i,"num_in_":result_item['custom_id'],"clinical_report":clinical_report,"response_diagnosis":response_diagnosis,"response_structured_data":response_structured_data })
            
            df_scenarios_save = pd.read_csv(os.path.join(path_results + job_name ,file_name.replace("json","csv") ),index_col=0)
            df_res_tmp = pd.DataFrame(prep_dict)
            df_res_tmp["num_in_"]=  df_res_tmp["num_in_"].astype(int)
            df_res_tmp = df_scenarios_save.merge(df_res_tmp,right_on="num_in_",left_index=True)
            now = dt.datetime.now()
            now_string = now.strftime("%Y%m%d%H%M%S%f")
            df_res_tmp = df_res_tmp.assign(encounter_id = now_string + df_res_tmp.bacth.apply(str) + df_res_tmp.num_in_.apply(str))
            df_res_tmp.encounter_id = df_res_tmp.encounter_id.str.pad(width=10, side='left', fillchar='0')
            df_res_final = pd.concat([df_res_final,df_res_tmp]) 

    df_res_final = df_res_final[df_res_final.clinical_report.notna()]

    df_res_final["icd_primary_pred"], df_res_final["icd_secondary_pred"],df_res_final["icd_coding_text"],df_res_final["icd_coding_list"] = zip(*df_res_final.apply(get_icd_coding_target,axis=1))

    return df_res_final