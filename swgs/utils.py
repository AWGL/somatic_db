def somatic_snv_tiering(somatic_snvs_query):
    """
    Tiering for somatic SNVs
    """
    # empty lists
    somatic_snvs_tier_one = []
    somatic_snvs_tier_two = []

    for v in somatic_snvs_query:
        variant = v.variant.variant
        gnomad = v.gnomad_popmax_af
        vaf = float(v.af) * 100
        vep_annotations = v.vep_annotations.first()
        hgvsc = vep_annotations.hgvsc
        hgvsp = vep_annotations.hgvsp
        gene = vep_annotations.transcript.gene.gene
        consequences = vep_annotations.consequence.all()
        impacts = list(set(consequence.impact.impact for consequence in consequences))
        consequences = [c.consequence for c in consequences]
        consequences_formatted = [c.replace("_", " ") for c in consequences]
        consequences_formatted = " | ".join(consequences)
        force_display = v.force_display()
        status = v.get_status_display()
        id = v.id
        var_type = "somatic"
        checks = v.get_all_checks()

        # handle gnomad
        if float(gnomad) == -1:
            gnomad_formatted = "Not in Gnomad"
        else:
            gnomad_formatted = f"{gnomad:.3f}%"

        # make variant dict
        variant_dict = {
                "pk": variant,
                "gnomad": gnomad_formatted,
                "vaf": f"{vaf:.2f}",
                "hgvsc": hgvsc,
                "hgvsp": hgvsp,
                "gene": gene,
                "consequence": consequences_formatted,
                "force_display": force_display,
                "status": status,
                "id": id,
                "var_type": var_type,
                "checks": checks

            }

        # lose >5% in gnomad and modifier only variants
        if float(gnomad) >= 0.05 or (len(impacts) == 1 and impacts[0] == "MODIFIER"):
            if not force_display:
                continue

        # Put in tier list
        if v.display_in_tier_zero():
            variant_dict["tier"] = "0"
            somatic_snvs_tier_one.append(variant_dict)
        elif v.display_in_tier_one():
            variant_dict["tier"] = "1"
            somatic_snvs_tier_one.append(variant_dict)
        elif v.display_in_tier_two():
            variant_dict["tier"] = "2"
            somatic_snvs_tier_two.append(variant_dict)
        else:
            pass

    return somatic_snvs_tier_one, somatic_snvs_tier_two


def germline_snv_tiering(germline_snvs_query):
    """
    Tiering for germline SNVs
    """

    germline_snvs_tier_one = []
    germline_snvs_tier_three = []

    for v in germline_snvs_query:
        variant = v.variant.variant
        gnomad = v.gnomad_popmax_af
        vaf = float(v.af) * 100
        vep_annotations = v.vep_annotations.first()
        hgvsc = vep_annotations.hgvsc
        hgvsp = vep_annotations.hgvsp
        gene = vep_annotations.transcript.gene.gene
        consequences = vep_annotations.consequence.all()
        impacts = list(set(consequence.impact.impact for consequence in consequences))
        consequences = [c.consequence for c in consequences]
        consequences_formatted = [c.replace("_", " ") for c in consequences]
        consequences_formatted = " | ".join(consequences)
        force_display = v.force_display()
        status = v.get_status_display()
        id = v.id
        var_type = "germline"
        checks = v.get_all_checks()

        # handle gnomad
        if float(gnomad) == -1:
            gnomad_formatted = "Not in Gnomad"
        else:
            gnomad_formatted = f"{gnomad:.3f}%"

        # make variant dict
        variant_dict = {
                "pk": variant,
                "gnomad": gnomad_formatted,
                "vaf": f"{vaf:.2f}",
                "hgvsc": hgvsc,
                "hgvsp": hgvsp,
                "gene": gene,
                "consequence": consequences_formatted,
                "force_display": force_display,
                "status": status,
                "id": id,
                "var_type": var_type,
                "checks": checks
            }

        # lose >5% in gnomad and modifier only variants
        if float(gnomad) >= 0.05 or (len(impacts) == 1 and impacts[0] == "MODIFIER"):
            if not force_display:
                continue

        # Put in tier list
        if v.display_in_tier_zero():
            variant_dict["tier"] = "0"
            germline_snvs_tier_one.append(variant_dict)
        elif v.display_in_tier_one():
            variant_dict["tier"] = "1"
            germline_snvs_tier_one.append(variant_dict)
        elif v.display_in_tier_three():
            variant_dict["tier"] = "3"
            germline_snvs_tier_three.append(variant_dict)
        else:
            pass
    
    return germline_snvs_tier_one, germline_snvs_tier_three

def germline_cnv_tiering(germline_cnvs_query):
    """
    Tiering for germline CNVs
    """
    germline_cnvs_tier_one = []
    germline_cnvs_tier_three = []

    for v in germline_cnvs_query:
        variant = v.cnv.variant
        svlen = v.cnv.svlen
        caller = v.cnv.caller
        gt = v.display_genotype()
        cn = v.cn
        try:
            maf = f"{(float(v.maf)*100):.1f}%"
        except TypeError:
            maf = "N/A"
        vep_annotations = v.vep_annotations.first()
        hgvsc = vep_annotations.hgvsc
        hgvsp = vep_annotations.hgvsp
        genes_tier_one = v.display_in_panel_genes("germline_cnv_tier_one")
        genes_tier_three = v.display_in_panel_genes("germline_cnv_tier_three")
        consequences = vep_annotations.consequence.all()
        impacts = list(set(consequence.impact.impact for consequence in consequences))
        consequences = [c.consequence for c in consequences]
        consequences_formatted = [c.replace("_", " ") for c in consequences]
        consequences_formatted = " | ".join(consequences)
        status = v.get_status_display()
        id = v.id
        var_type = "germline"
        #checks = v.get_all_checks()

        # make variant dict
        variant_dict = {
                "pk": variant,
                "gt": gt,
                "cn": cn,
                "maf": maf,
                "hgvsc": hgvsc,
                "hgvsp": hgvsp,
                "genes_tier_one": genes_tier_one,
                "genes_tier_three": genes_tier_three,
                "consequence": consequences_formatted,
                "status": status,
                "id": id,
                "var_type": var_type,
                #"checks": checks,
                "cnv_or_sv": "cnv",
                "caller": caller,
                "svlen": svlen        
            }

        # Put in tier list
        if v.display_in_tier_zero():
            variant_dict["tier"] = "0"
            germline_cnvs_tier_one.append(variant_dict)
        elif v.display_in_tier_one():
            variant_dict["tier"] = "1"
            germline_cnvs_tier_one.append(variant_dict)
        elif v.display_in_tier_three():
            variant_dict["tier"] = "3"
            germline_cnvs_tier_three.append(variant_dict)
        else:
            pass

    return germline_cnvs_tier_one, germline_cnvs_tier_three

def germline_sv_tiering(germline_svs_query):
    """
    Tiering for germline SVs, excluding BNDs
    """
    germline_svs_tier_one = []
    germline_svs_tier_three = []

    for v in germline_svs_query:
        variant = v.sv.variant
        svlen = v.sv.svlen
        caller = v.sv.caller
        pr = v.pr
        sr = v.sr
        vf = v.vf
        imprecise = v.imprecise
        somatic_score = v.somatic_score
        vep_annotations = v.vep_annotations.first()
        hgvsc = vep_annotations.hgvsc
        hgvsp = vep_annotations.hgvsp
        genes_tier_one = v.display_in_panel_genes("germline_cnv_tier_one")
        genes_tier_three = v.display_in_panel_genes("germline_cnv_tier_three")
        consequences = vep_annotations.consequence.all()
        impacts = list(set(consequence.impact.impact for consequence in consequences))
        consequences = [c.consequence for c in consequences]
        consequences_formatted = [c.replace("_", " ") for c in consequences]
        consequences_formatted = " | ".join(consequences)
        status = v.get_status_display()
        id = v.id
        var_type = "germline"
        #checks = v.get_all_checks()

        # make variant dict
        variant_dict = {
                "pk": variant,
                "pr": pr,
                "sr": sr,
                "vf": vf,
                "imprecise": imprecise,
                "somatic_score": somatic_score,
                "hgvsc": hgvsc,
                "hgvsp": hgvsp,
                "genes_tier_one": genes_tier_one,
                "genes_tier_three": genes_tier_three,
                "consequence": consequences_formatted,
                "status": status,
                "id": id,
                "var_type": var_type,
                #"checks": checks,
                "cnv_or_sv": "cnv",
                "caller": caller,
                "svlen": svlen
            }

        # Put in tier list
        if v.display_in_tier_zero():
            variant_dict["tier"] = "0"
            print("0")
            germline_svs_tier_one.append(variant_dict)
        elif v.display_in_tier_one():
            variant_dict["tier"] = "1"
            print("1")
            germline_svs_tier_one.append(variant_dict)
        elif v.display_in_tier_three():
            variant_dict["tier"] = "3"
            print("3")
            germline_svs_tier_three.append(variant_dict)
        else:
            print("pass")
            pass

    return germline_svs_tier_one, germline_svs_tier_three

def somatic_cnv_tiering(somatic_cnvs_query):
    """
    Tiering for somatic CNVs
    """
    somatic_cnvs_domain_one = []
    somatic_cnvs_domain_two = []

    for v in somatic_cnvs_query:
        variant = v.cnv.variant
        svlen = v.cnv.svlen
        caller = v.cnv.caller
        gt = v.display_genotype()
        cn = v.cn
        try:
            maf = f"{(float(v.maf)*100):.1f}%"
        except TypeError:
            maf = "N/A"
        vep_annotations = v.vep_annotations.first()
        hgvsc = vep_annotations.hgvsc
        hgvsp = vep_annotations.hgvsp
        genes_domain_one = v.display_in_panel_genes("somatic_cnv_domain_one")
        genes_domain_two = v.display_in_panel_genes("somatic_cnv_domain_two")
        consequences = vep_annotations.consequence.all()
        impacts = list(set(consequence.impact.impact for consequence in consequences))
        consequences = [c.consequence for c in consequences]
        consequences_formatted = [c.replace("_", " ") for c in consequences]
        consequences_formatted = " | ".join(consequences)
        status = v.get_status_display()
        id = v.id
        var_type = "somatic"
        #checks = v.get_all_checks()

        # make variant dict
        variant_dict = {
                "pk": variant,
                "gt": gt,
                "cn": cn,
                "maf": maf,
                "hgvsc": hgvsc,
                "hgvsp": hgvsp,
                "genes_domain_one": genes_domain_one,
                "genes_domain_two": genes_domain_two,
                "consequence": consequences_formatted,
                "status": status,
                "id": id,
                "var_type": var_type,
                #"checks": checks,
                "cnv_or_sv": "cnv",
                "caller": caller,
                "svlen": svlen
            }

        # Put in tier list
        if v.display_in_domain_zero():
            variant_dict["tier"] = "0"
            somatic_cnvs_domain_one.append(variant_dict)
        elif v.display_in_domain_one():
            variant_dict["tier"] = "1"
            somatic_cnvs_domain_one.append(variant_dict)
        elif v.display_in_domain_two():
            variant_dict["tier"] = "2"
            somatic_cnvs_domain_two.append(variant_dict)
        else:
            pass

    return somatic_cnvs_domain_one, somatic_cnvs_domain_two


def somatic_sv_tiering(somatic_svs_query):
    """
    Tiering for germline SVs, excluding BNDs
    """
    somatic_svs_domain_one = []
    somatic_svs_domain_two = []

    for v in somatic_svs_query:
        variant = v.sv.variant
        svlen = v.sv.svlen
        caller = v.sv.caller
        pr = v.pr
        sr = v.sr
        vf = v.vf
        imprecise = v.imprecise
        somatic_score = v.somatic_score
        vep_annotations = v.vep_annotations.first()
        hgvsc = vep_annotations.hgvsc
        hgvsp = vep_annotations.hgvsp
        genes_domain_one = v.display_in_panel_genes("somatic_cnv_domain_one")
        genes_domain_two = v.display_in_panel_genes("somatic_cnv_domain_two")
        consequences = vep_annotations.consequence.all()
        impacts = list(set(consequence.impact.impact for consequence in consequences))
        consequences = [c.consequence for c in consequences]
        consequences_formatted = [c.replace("_", " ") for c in consequences]
        consequences_formatted = " | ".join(consequences)
        status = v.get_status_display()
        id = v.id
        var_type = "somatic"
        #checks = v.get_all_checks()

        # make variant dict
        variant_dict = {
                "pk": variant,
                "pr": pr,
                "sr": sr,
                "vf": vf,
                "imprecise": imprecise,
                "somatic_score": somatic_score,
                "hgvsc": hgvsc,
                "hgvsp": hgvsp,
                "genes_domain_one": genes_domain_one,
                "genes_domain_two": genes_domain_two,
                "consequence": consequences_formatted,
                "status": status,
                "id": id,
                "var_type": var_type,
                #"checks": checks,
                "cnv_or_sv": "cnv",
                "caller": caller,
                "svlen": svlen
            }

        # Put in tier list
        if v.display_in_domain_zero():
            variant_dict["tier"] = "0"
            somatic_svs_domain_one.append(variant_dict)
        elif v.display_in_domain_one():
            variant_dict["tier"] = "1"
            somatic_svs_domain_one.append(variant_dict)
        elif v.display_in_domain_two():
            variant_dict["tier"] = "2"
            somatic_svs_domain_two.append(variant_dict)
        else:
            pass

    return somatic_svs_domain_one, somatic_svs_domain_two