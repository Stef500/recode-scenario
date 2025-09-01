import pandas as pd
import numpy as np
import datetime as dt
import re
import datetime
import random
# Usefull functions



def random_date(year,exclude_weekends=False):
  """   
  Generates a random date in the year 2024.

  Args:
    exclude_weekends: If True, excludes Saturdays and Sundays.
  """

  while True:
    year = 2024
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

def get_dates_of_stay(admission_type, admission_mode,mols,sdlos):
    """
    Generate date of entry and date of discharge from Mean Length of Stay (MLOS) and Standard Deviaton length of stay (DSLOS)
    """

    if admission_type == "Outpatient" :
        date_entry = date_discharge = random_date(2024,exclude_weekends=False)

    else:
        # los can be negative if we do like this
        #los = int(np.round(np.random.normal(mols, sdlos, 1))[0]) 
        
        los = int(np.abs(np.random.normal(mols, sdlos, 1)[0])) 


        if admission_mode=="URGENCES":
            date_entry = random_date(2024,exclude_weekends=False)
        else :
            date_entry = random_date(2024,exclude_weekends=True)

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

        # Recoding french names
        #TODO : other variables : adminission mode
        self.recoding_dict ={"HP":"Outpatient","HC":"Inpatient"}
        
        self.icd_codes_cancer_meta_ln= ["C770","C771","C772","C773","C774","C775","C778","C779"]
        self.icd_codes_cancer_meta = ["C780","C781","C782","C783","C784","C785","C786","C787","C788",
                    "C790","C791","C792","C793","C794","C795","C796","C797","C798"]

        self.drg_parent_code_chimio = ['28Z07','17M05','17M06']
        self.drg_parent_code_radio = ["17K04","17K05","17K08","17K09","28Z10","28Z11","28Z18","28Z19",
                        "28Z20","28Z21","28Z22","28Z23","28Z24","28Z25"]
        self.drg_parent_code_greffe = ["27Z02","27Z03","27Z04"]
        self.drg_parent_code_transfusion = ["28Z14"]
        self.drg_parent_code_palliative_care = ["23Z02"]
        self.drg_parent_code_stomies = ["06M17"]
        self.drg_parent_code_apheresis = ["28Z16"]
        self.drg_parent_code_deceased = ["04M24"]
        self.drg_parent_code_bilan = ["23M03"]

        self.icd_codes_cancer = pd.read_excel(path_ref + "REFERENTIEL_METHODE_DIM_CANCER_20140411.xls")
        self.icd_codes_cancer = self.icd_codes_cancer.CIM10.to_list()
        # Add icd_parent_code to list, but not very elgant, it will be usefull as some of icd codes that will tested to be 
        # in that list are actualy icd_parent_code
        #TODO : Find an other way...
        self.icd_codes_cancer = list(set([code[0:3] for code in self.icd_codes_cancer])) + self.icd_codes_cancer

        self.drg_statistics = pd.read_excel(path_ref + "stat_racines.xlsx")
        self.drg_statistics.rename(columns = {"racine":"drg_parent_code","dms":"los_mean","dsd":"los_sd"},inplace=True)

        self.df_icd_synonyms = pd.read_csv(path_ref + "cim_synonymes.csv").dropna()
        self.df_icd_synonyms.rename(columns = {"dictionary_keys":"icd_code_description","code":"icd_code"},inplace=True)

        self.df_chronic = pd.read_excel(path_ref + "Affections chroniques.xlsx",header=None,names=["code","chronic","libelle"])
        self.icd_codes_chronic = self.df_chronic.code[self.df_chronic.chronic.isin([1,2,3])]

        self.drg_parents_groups = pd.read_excel(self.path_ref + "ghm_rghm_regroupement_2024.xlsx")
        self.drg_parents_groups.rename(columns={"racine":"drg_parent_code","libelle_racine":"drg_parent_description"},inplace=True)

        self.df_names = pd.read_csv(path_ref + "prenoms_nom_sexe.csv",sep=";").dropna()


        self.icd_code_chronic_attack = pd.read_csv(path_ref + "icd_code_chronic_attack.txt",sep=";").code


     
    def load_offical_icd(self,
                        file_name : str,
                        col_names: dict | None = None ):

        self.df_icd_official = pd.read_excel(self.path_ref + file_name )

        if col_names is not None : 
            self.df_icd_official.rename(columns = col_names, inplace = True)
            
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



    def load_classification_profile(self,
                       file_name : str,
                        col_names: dict | None = None ):

        self.df_classification_profile = pd.read_csv(self.path_data + file_name,sep=";")
        
        if col_names is not None : 
            self.df_classification_profile.rename(columns = col_names, inplace = True) 
        
        self.df_classification_profile = self.df_classification_profile.merge(self.drg_statistics,how="left")
        self.df_classification_profile= self.df_classification_profile.merge(self.drg_parents_groups,how="left")
        self.df_classification_profile = self.df_classification_profile.assign(admission_type = self.df_classification_profile.admission_type.replace(self.recoding_dict))
        self.df_classification_profile = self.df_classification_profile.merge(self.ref_sep[["age","specialty","drg_parent_code"]],how="left")
        self.df_classification_profile.los_mean[(self.df_classification_profile.los_mean.isna())] = 0
        self.df_classification_profile.los_sd[(self.df_classification_profile.los_sd.isna())] = 0

    def load_referential_hospital(self,
                       file_name : str,
                       col_names: list = ["hospital"] ):
        
        self.df_hospitals = pd.read_csv(self.path_ref+ file_name, names = col_names)

    def load_exclusions(self,
                       file_name : str,
                       col_names: dict | None = None):
        
        self.df_exclusions = pd.read_csv(self.path_ref+ file_name)

        if col_names is not None : 
            self.df_classification_profile.rename(columns = col_names, inplace = True) 


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
                       max_nb : int | None = 5 ,
                       distinct_chapter : bool = False,
                       ):

        """

        ### Attribute DAS to each situations

        Function to attribute DAS for each key (sexe,new_cage,categ_cim):
        - Metastase :
        * choose randomly if patient has a metastase regarding metastasis distribution
        * choose randomly the number of metastasis in df_das_new_meta_n_distinct
        * choose randomly the metastic codes in df_das_new_meta regarding distribution of case (nb_das)
        - Chronic disease :
        * choose randomly the number of chronic disease in regard with df_das_new_chronic_n_distinct taking into account a zero option
        * choose randomly the list of chronic disease in the df_das_new_chronic dataset regarding distribution of case (nb_das)
        - Complication :
        * choose randomly the number of complications in regard with df_das_new_complication_n_distinct taking into account a zero option
        * choose randomly the list of complications in the df_das_new_complication dataset regarding distribution of case (nb_das)

        For each ICD code at the end choose the right formulation in the


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
                'icd_secondaray_code':[],
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
                'last_name_med':None
                
             
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

    def define_cancer_md_pec(self,case):
        situa = ""
        code = -1

        if case["histological_type"] is not None:
            situa = "Hospitalisation pour prise en charge du cancer"
            code = 0
        
        elif case["drg_parent_code"] in self.drg_parent_code_chimio and case["admission_type"]  == "Outpatient" :
            situa = "Prise en charge en hospitalisation de jour pour cure de chimiothérapie"
            
        if case["drg_parent_code"] in self.drg_parent_code_chimio and case["admission_type"]  == "Outpatient" :
            situa = "Prise en charge en hospitalisation de jour pour cure de chimiothérapie"
            if case["chemotherapy_regimen"] is not None and not (isinstance(case["chemotherapy_regimen"], float)):
                situa += ". Le protocole actuellement suivi est : "+ case["chemotherapy_regimen"]
            code = 1

        elif case["drg_parent_code"] in self.drg_parent_code_chimio and case["admission_type"]  == "Inpatient":
            situa = "Prise en charge en hospitalisation complète pour cure de chimiothérapie"
            if case["chemotherapy_regimen"] is not None and not (isinstance(case["chemotherapy_regimen"], float)): 
                situa += ". Le protocole actuellement suivi est : "+ case["chemotherapy_regimen"]
            code = 2

        elif case["drg_parent_code"] in self.drg_parent_code_radio and case["admission_type"]  == "Outpatient":
            situa = "Prise en charge en hospitalisation de jour pour séance de radiothérapie"
            code = 3

        elif case["drg_parent_code"] in self.drg_parent_code_radio and case["admission_type"]  == "Inpatient":
            situa = "Prise en charge en hospitalisation complète pour réalisation du traitment de radiothérapie"
            code = 4

        elif case["drg_parent_code"] in self.drg_parent_code_greffe:
            situa = "Prise en charge pour " + case["drg_parent_description"].lower()
            code = 5

        elif case["drg_parent_code"] in self.drg_parent_code_transfusion :
            situa = "Prise en charge pour " + case["drg_parent_description"].lower()
            code = 6

        elif case["drg_parent_code"] in self.drg_parent_code_apheresis :
            situa = "Prise en charge pour " + case["drg_parent_description"].lower()
            code = 7

        elif case["drg_parent_code"] in self.drg_parent_code_palliative_care :
            situa = "Prise en charge pour soins palliatifs"
            code = 8

        elif case["drg_parent_code"] in self.drg_parent_code_stomies:
            situa = "Prise en charge pour " + case["drg_parent_description"].lower()
            code = 9

        elif (case["drg_parent_code"] in self.drg_parent_code_deceased) | (case["discharge_disposition"] == "DECES"):
            situa =  "Hospitalisation au cours de laquelle le patient est décédé"
            code = 10

        elif case["drg_parent_code"][2:3] in ["C"] and case["admission_type"]  == "Outpatient" :
            situa =  "Prise en charge en chirugie ambulatoire pour "

            if case["text_procedure"] != "" :
                situa += case["text_procedure"].lower()
                
            code = 11

        elif case["drg_parent_code"][2:3] in ["C"] and case["admission_type"]  == "Inpatient" :
            situa =  "Prise en charge chirugicale en hospitalisation complète pour "

            if case["text_procedure"] != "" :
                situa += case["text_procedure"].lower()

                code = 12
                
        elif case["drg_parent_code"][2:3] in ["K"] and case["admission_type"]  == "Outpatient" :
            situa =  "Prise en charge en ambulatoire pour "

            if case["text_procedure"] != "" :
                situa += case["text_procedure"].lower()

            code = 13

        elif case["drg_parent_code"][2:3] in ["K"] and case["admission_type"]  == "Inpatient" :
            situa =  "Prise en charge en hospitalisation complète pour "

            if case["text_procedure"] != "" :
                situa += case["text_procedure"].lower()

                code = 14
        else :
            if case["icd_primary_code"] in self.icd_codes_cancer : 

                if    case["case_management_type"][0:1]=="Z" :
                                     
                    situa =  "Hospitalisation en ambulatoire pour " + case["case_management_type_description"]
                    code = 15
                    # print(code)
                    
                else:
                    option = np.random.choice(2, p=[0.6, 0.4])
                    if option == 0:
                            situa = "Première hospitalisation pour découverte de cancer" # 60%
                            code = 16

                    elif option == 1:
                        situa = "Première prise en charge diagnostique et thérapeutique dans le cadre d'une rechute du cancer après traitement" # 40%
                        code = 17

  
            else :
                    if case["admission_type"]  == "Outpatient" :
                        
                        if case["case_management_type"]  == "DP":
                            situa =  "Hospitalisation pour prise en charge diagnostique et thérapeutique du diagnotic principal en ambulatoire" # 30%
                            code = 18
                            # print(code)
                        else:
                            situa =  "Hospitalisation en ambulatoire pour " + case["case_management_type_description"]
                            code = 19
                            # print(code)
                    else :
                        if case["case_management_type"]  == "DP":
                            situa =  "Hospitalisation pour prise en charge diagnostique et thérapeutique du diagnotic principal en hospitalisation complète" # 30%
                            code = 20
                            # print(code)
                        else:
                            situa =  "Hospitalisation en hospitalisation complète pour " + case["case_management_type_description"]
                            code = 21
                            # print(code)
        return (situa, code)
            
        


   


    def generate_scenario_from_profile(self,
                                       profile):
        
        profile["icd_parent_code"] = profile["icd_primary_code"][0:3]

        scenario = self.get_clinical_scenario_template()

        is_cancer = 0
        for k,v in profile.items():
            scenario[k]=v 

        ### Principals diagnosis
        scenario["icd_primary_description"] = self.get_icd_description(profile.icd_primary_code)

        # scenario["icd_primary_description_alternative"] = self.get_icd_alternative_descriptions(profile.icd_primary_code)
        scenario["case_management_type_description"] = self.get_icd_description(profile.case_management_type)

        ### Administratives elements
        scenario["age"] = get_age(profile.cage)
        scenario["date_entry"],scenario["date_discharge"] = get_dates_of_stay(profile.admission_type,profile.admission_mode,profile.los_mean,profile.los_sd)
        scenario["date_of_birth"] = random_date_between( scenario["date_entry"] - datetime.timedelta(days = 365*(scenario["age"]+1)) , scenario["date_entry"] - datetime.timedelta(days = 365*(scenario["age"])))
        scenario["first_name"] , scenario["last_name"] = self.get_names(profile.sexe)
        scenario["first_name_med"] , scenario["last_name_med"] = self.get_names(random.randint(1, 2))

        scenario["departement"] = profile["specialty"]

        scenario["hospital"] =   self.df_hospitals.sample(1)['hospital'].iloc[0]
        

        ### Secondary diagnosis :
        ### We sample secondary diagnosis by steps : metastases, metastases ln, chronic,complications
        ### Each time build :
        ### - official descriptions
        ### - official : alternatives descripttion
        scenario["text_secondary_icd_official"]=""
        # scenario["text_secondary_icd_alternative"]=""

        grouping_secondary =["icd_primary_code","icd_secondary_code","cage2","sexe","nb"] 

        ### Scenarios will be much more different when clinical case is about cancer
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
            
            ### Categories of chronic desease : when cancer you don't sample chronic diseases over cancer icd codes


        ### Treatment recommandations for cancer :
        if is_cancer ==1 :
            chronic_diseases = self.sample_from_df(profile =profile,df_values= self.df_secondary_icd.query("type.isin(['Chronic'])")[grouping_secondary], distinct_chapter=True)

        else :     
            # chronic_diseases =  self.sample_from_df(profile =profile,df_values= self.df_secondary_icd.query("type.isin(['Chronic'])")[grouping_secondary]) 
            df_values = self.df_secondary_icd.query("type.isin(['Chronic'])")[grouping_secondary]
            df_secondary_cancer = self.df_secondary_icd[self.df_secondary_icd.icd_secondary_code.isin(self.icd_codes_cancer)][grouping_secondary]
            
            df_values = pd.concat([df_values, df_secondary_cancer])
            chronic_diseases =  self.sample_from_df(profile =profile,df_values=df_values, distinct_chapter=True)  

        if chronic_diseases.shape[0] > 0 :
            for index, row in chronic_diseases.iterrows():
                scenario["text_secondary_icd_official"] += "- " + row.icd_code_description_official + " ("+ row.icd_secondary_code+")\n"
                # scenario["text_secondary_icd_alternative"] += "- " + row.icd_code_description_official + "("+ row.icd_secondary_code+") : " + row.icd_code_description_alternative + "\n"
            
            scenario["icd_secondaray_code"] = chronic_diseases.icd_secondary_code.to_list()

        ### Is we sampled cancer codes in the chronic disease we will also sample metastasis
        if len(scenario["icd_secondaray_code"])>0 :
            if bool(set(scenario["icd_secondaray_code"]) & set(self.icd_codes_cancer)) :
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

                        scenario["icd_secondaray_code"] = scenario["icd_secondaray_code"] + metastases_ln.icd_secondary_code.to_list()

                if bool(re.search("M[123x+]",scenario["score_TNM"])) :
                    metastases = self.sample_from_df(profile =profile,df_values= self.df_secondary_icd.query("type=='Metastasis'")[grouping_secondary])  
            
                    if metastases.shape[0] > 0 :
                            for index, row in metastases.iterrows():
                                scenario["text_secondary_icd_official"] += "- " + row.icd_code_description_official + " ("+ row.icd_secondary_code+")\n"
                                # scenario["text_secondary_icd_alternative"] += "- " + row.icd_code_description_official + "("+ row.icd_secondary_code+") : " + row.icd_code_description_alternative + "\n"

                            scenario["icd_secondaray_code"] = scenario["icd_secondaray_code"] + metastases.icd_secondary_code.to_list()
                    
            
            #When TNM is not known, sample metastasis among all possible situations
            else:
                metastases = self.sample_from_df(profile =profile,df_values= self.df_secondary_icd.query("type.isin(['Metastasis','Metastasis LN'])")[grouping_secondary])  
            
                if metastases.shape[0] > 0 :
                    for index, row in metastases.iterrows():
                        scenario["text_secondary_icd_official"] += "- " + row.icd_code_description_official + " ("+ row.icd_secondary_code+")\n"
                        # scenario["text_secondary_icd_alternative"] += "- " + row.icd_code_description_official + "("+ row.icd_secondary_code+") : " + row.icd_code_description_alternative + "\n"
                        
                    scenario["icd_secondaray_code"] = scenario["icd_secondaray_code"] + metastases.icd_secondary_code.to_list()

        #For complication drg_parent_code we choose grouping profile only on ICD
        grouping_secondary =["drg_parent_code","icd_secondary_code","cage2","sexe","nb"]

        complications = self.sample_from_df(profile =profile,df_values= self.df_secondary_icd.query("type.isin(['Acute'])")[grouping_secondary]) 

        if complications.shape[0] > 0 :
            for index, row in complications.iterrows():
                scenario["text_secondary_icd_official"] += "- " + row.icd_code_description_official + " ("+ row.icd_secondary_code+")\n"
                # scenario["text_secondary_icd_alternative"] += "- " + row.icd_code_description_official + "("+ row.icd_secondary_code+") : " + row.icd_code_description_alternative + "\n"
            
        scenario["icd_secondaray_code"] = scenario["icd_secondaray_code"] + complications.icd_secondary_code.to_list()

        ## Actes

        grouping_procedure =["procedure","drg_parent_code","icd_primary_code","cage2","sexe"]
        procedures = self.sample_from_df(profile =profile,df_values= self.df_procedures[grouping_procedure],nb=1) 

        scenario["procedure"] = procedures.procedure.to_list()

        scenario["text_procedure"] = ""

        for index, row in procedures.iterrows():
                scenario["text_procedure"] += "- " + row.procedure_description_official + " ("+ row.procedure+")\n"


        scenario["case_management_type_text"] , scenario["cd_md_pec"] = self.define_cancer_md_pec(scenario)

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
                SCENARIO +="- Mode de prise en charge : "+ scenario["case_management_type_text"] + "\n" 
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
                template_name = "surgery_complete_onco.txt"
            elif scenario['admission_type'] == "Outpatient" and scenario['drg_parent_code'][2:3]=="C" :
                template_name = "surgery_outpatient_onco.txt"
            else:
                template_name = "scenario_onco_v1.txt"
        
        else:
            if scenario['admission_type'] == "Inpatient" and scenario['drg_parent_code'][2:3]=="C" :
                template_name = "surgery_complete_onco.txt"
            elif scenario['admission_type'] == "Outpatient" and scenario['drg_parent_code'][2:3]=="C" :
                template_name = "surgery_outpatient_onco.txt"
            else:
                template_name = "scenario_onco_v1.txt"            
            
        with open("templates/" + template_name, "r", encoding="utf-8") as f:
            prompt = f.read()
        
        return prompt
