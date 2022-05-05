# @main.command()
# @click.pass_context
# def process_all(ctx):
# 	click.echo("Capitalize Name :: {}".format(ctx.obj['config'].title()))

# Parent Command
# @click.group(chain=True)
# @click.option('--config', default = "./config/config.yaml")
# @click.pass_context
# def main(ctx,config):
# 	"""A Simple CLI with Group"""
# 	ctx.ensure_object(dict)

# 	ctx.obj['config'] = config

# # Child Command
# @main.command()
# @click.pass_context
# def process_files(ctx):
# 	"""Reverse A text"""
# 	config_file = ctx.obj['config']
# 	click.echo("config_file: {}".format(config_file))

# @main.command()
# @click.pass_context
# def process_all(ctx):
# 	"""Capitalize A Text"""
#     click.echo("process all")
    # config_file = ctx.obj['config']
	# click.echo("config_file: {}".format(config_file))
# @click.command()
# @click.option('--firstname', '-f', help = "First Name Desceription", type = str, default ="Friends")
# @click.version_option('0.0.1', prog_name="basic_cli")

# def main(firstname):
#     print(f"Hello CLI {firstname}")


# if __name__ == "__main__":
#     # main()