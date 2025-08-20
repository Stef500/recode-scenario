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

def get_dates_of_stay(type_hospitalisation, entry_mode,mols,sdlos):
    """
    Generate date of entry and date of discharge from Mean Length of Stay (MLOS) and Standard Deviaton length of stay (DSLOS)
    """

    if type_hospitalisation == "HP" :
        date_entry = date_discharge = random_date(2024,exclude_weekends=False)

    else:
        los = int(np.round(np.random.normal(mols, sdlos, 1))[0])


        if entry_mode=="URGENCES":
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
        self.icd_codes_cancer = self.icd_codes_cancer.CIM10

        self.drg_statistics = pd.read_excel(path_ref + "stat_racines.xlsx")
        self.drg_statistics.rename(columns = {"racine":"drg_parent_code","dms":"los_mean","dsd":"los_sd"},inplace=True)

        self.df_icd_synonyms = pd.read_csv(path_ref + "cim_synonymes.csv").dropna()
        self.df_icd_synonyms.rename(columns = {"dictionary_keys":"icd_code_description","code":"icd_code"},inplace=True)

        self.df_chronic = pd.read_excel(path_ref + "Affections chroniques.xlsx",header=None,names=["code","chronic","libelle"])
        self.icd_codes_chronic = self.df_chronic.code[self.df_chronic.chronic.isin([1,2,3])]

        self.drg_parents_groups = pd.read_excel(self.path_ref + "ghm_rghm_regroupement_2024.xlsx")
        self.drg_parents_groups.rename(columns={"racine":"drg_parent_code","libelle_racine":"drg_parent_description"},inplace=True)

        self.df_names = pd.read_csv(path_ref + "prenoms_nom_sexe.csv",sep=";").dropna()

     
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

    def load_classification_profile(self,
                       file_name : str,
                        col_names: dict | None = None ):

        self.df_classification_profile = pd.read_csv(self.path_data + file_name,sep=";")
        
        if col_names is not None : 
            self.df_classification_profile.rename(columns = col_names, inplace = True) 
        
        self.df_classification_profile = self.df_classification_profile.merge(self.drg_statistics,how="left")
        self.df_classification_profile= self.df_classification_profile.merge(self.drg_parents_groups,how="left")

    def load_secondary_icd(self,
                       file_name : str,
                       col_names: dict | None = None  ):
        """
        Related diagnosis are segmented in chronical deseases and complications (acute diseases). 
        For cancer we build specific categories : primitive, lymph node metastasis, other metastasis.

        To facilitate sample among related diagnosis, we calculate for each sitution the total number of possible related diagnosis.

        """
        self.df_secondary_icd = pd.read_csv(self.path_data + "bn_pmsi_related_diag_20250818.csv",sep=";")

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
        
        
        if df_sel.shape[0] ==0 :
            return pd.DataFrame(columns=df_values.columns)

        nb_sample_max = np.minimum(df_sel.shape[0],max_nb)

        #If nb is present, the number of samples if fixed and equal to the max possible.
        if nb is not None :
            nb_final_sample = nb_sample_max
        else:
            nb_final_sample = np.random.randint(nb_sample_max, size=1)[0]


        if nb_final_sample > 0:

            #Codes are from different chapter of ICD10
            if distinct_chapter == True and "icd_secondary_code" in df_sample.columns:

                df_sample=None
                chapter = []

                for i in range(1,nb_final_sample+1):
                    df_sample=pd.concat([df_sample,df_sel[~(df_sel.icd_secondary_code.str.slice(0,1).isin(chapter))].sample(1, replace=False, weights = col_weights  )])
                    chapter = df_sample.icd_secondary_code.str.slice(0,1).to_list()

            else:
                df_sample= df_sel.sample(nb_final_sample, replace=False, weights =col_weights)

            # Add description codes
            if  "icd_secondary_code" in df_sample.columns   :
                df_sample["icd_code_description_alternative"] = df_sample.icd_secondary_code.apply(self.get_n_icd_alternative_descriptions)
                df_sample["icd_code_description_official"] = df_sample.icd_secondary_code.apply(self.get_icd_description)
                
                return df_sample[["icd_secondary_code","icd_code_description_official","icd_code_description_alternative"]].reset_index(  drop=True  )

            elif "procedure" in df_sample.columns  :
                df_sample["procedure_description_official"] = df_sample.procedure.apply(self.get_procedure_description)
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
                'laste_name':None,
                'icd_primariry_code':None,
                'icd_primary_code_definition': None,
                'icd_primary_code_definition_alternatives': None,
                'cancer_histology':None,
                'TNM_score':None,
                'cancer_stage':None,
                'biomarqueurs':None,
                'chemotherapy_protocole':None,
                'case_management_type':None,
                'icd_secondaray_codes':None,
                'df_icd_secondaray_codes':None,
                'mode_entree':None,
                'mode_sortie':None,
                
             
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
        code = 0

        if case["drg_parent_code"] in self.drg_parent_code_chimio and case["mode_hospit"]  == "HP" :
            situa = "Prise en charge en hospitalisation de jour pour cure de chimiothérapie"
            code = 1

        elif case["drg_parent_code"] in self.drg_parent_code_chimio and case["mode_hospit"]  == "HC":
            situa = "Prise en charge en hospitalisation complète pour cure de chimiothérapie"
            if case["chemotherapy_protocole"] is not None :
                situa += ".Le protocole actuellement suivi est : "+ case["chemotherapy_protocole"]
            code = 2

        elif case["drg_parent_code"] in self.drg_parent_code_radio and case["mode_hospit"]  == "HP":
            situa = "Prise en charge en hospitalisation de jour pour séance de radiothérapie"
            code = 3

        elif case["drg_parent_code"] in self.drg_parent_code_radio and case["mode_hospit"]  == "HC":
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

        elif (case["drg_parent_code"] in self.drg_parent_code_deceased) | (case["mode_sortie"] == "DECES"):
            situa =  "Hospitalisation au cours de laquelle le patient est décédé"
            code = 10

        elif case["drg_parent_code"][2:3] in ["C"] and case["type_hosp"]  == "HP" :
            situa =  "Prise en charge en chirugie ambulatoire pour "
    

            if situa.actes != "" :
                situa += situa.actes.lower()

            code = 11

        elif case["drg_parent_code"][2:3] in ["C"] and case["mode_hospit"]  == "HC" :
            situa =  "Prise en charge chirugicale en hospitalisation complète pour "

            if situa.actes != "" :
                situa += situa.actes.lower()

                code = 12

        else :
            if case["icd_primary_code"] in self.icd_codes_cancer : 

                option = np.random.choice(3, p=[0.4, 0.3, 0.3])
                if option == 0:
                        situa = "Première hospitalisation pour découverte de cancer" # 40%
                        code = 13

                elif option == 1:
                    situa = "Première diagnostique et thérapeutique dans le cadre d'une rechute du cancer après traitement" # 30%
                    code = 14

                else:
                    situa =  "Hospitalisation pour bilan et surveillance du cancer" # 30%
                    code = 15
            else :
                    if case["mode_hospit"]  == "HP" :
                        
                        if case["case_management_type"]  == "DP":
                            situa =  "Hospitalisation pour prise en charge diagnostique et thérapeutique du diagnotic principal en ambulatoire" # 30%
                            code = 16
                            print(code)
                        else:
                            situa =  "Hospitalisation en ambulatoire pour " + case["case_management_type_description"]
                            code = 17
                            print(code)
                    else :
                        if case["case_management_type"]  == "DP":
                            situa =  "Hospitalisation pour prise en charge diagnostique et thérapeutique du diagnotic principal en hospitalisation complète" # 30%
                            code = 18
                            print(code)
                        else:
                            situa =  "Hospitalisation en hospitalisation complète pour " + case["case_management_type_description"]
                            code = 19
                            print(code)
        return (situa, code)
            
        


